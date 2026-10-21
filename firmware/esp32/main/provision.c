/* UART provisioning REPL for the ESP32-S3 scaffold. The REPL is the offline
 * path for Wi-Fi/controller/pairing when the device has no network yet. */
#include "provision.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "app_config.h"
#include "audio_capture.h"
#include "audio_playback.h"
#include "device_session.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "math.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "servo_yaw.h"
#include "status_led.h"
#include "lcd_ili9341.h"

static const char *TAG = "provision";

static int cmd_provision(int argc, char **argv) {
    if (argc != 6) {
        printf("usage: provision <ssid> <pass> <controller_url> <meeting_id> <media_token>\n");
        return ESP_ERR_INVALID_ARG;
    }
    nvs_handle_t h;
    esp_err_t rc = nvs_open(EFFMEET_NVS_NAMESPACE, NVS_READWRITE, &h);
    if (rc != ESP_OK) {
        return rc;
    }
    nvs_set_str(h, "wifi_ssid", argv[1]);
    nvs_set_str(h, "wifi_pass", argv[2]);
    nvs_set_str(h, "controller_url", argv[3]);
    nvs_set_str(h, "meeting_id", argv[4]);
    nvs_set_str(h, "media_token", argv[5]);
    rc = nvs_commit(h);
    nvs_close(h);
    if (rc != ESP_OK) {
        return rc;
    }
    printf("provisioned; rebooting\n");
    vTaskDelay(pdMS_TO_TICKS(200));
    esp_restart();
    return ESP_OK;
}

static int cmd_provision_status(int argc, char **argv) {
    (void)argc; (void)argv;
    nvs_handle_t h;
    if (nvs_open(EFFMEET_NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) {
        printf("NVS namespace not found; nothing provisioned.\n");
        return ESP_OK;
    }
    char ssid[64] = {0}, controller[128] = {0}, meeting[37] = {0};
    size_t n;
    n = sizeof(ssid); nvs_get_str(h, "wifi_ssid", ssid, &n);
    n = sizeof(controller); nvs_get_str(h, "controller_url", controller, &n);
    n = sizeof(meeting); nvs_get_str(h, "meeting_id", meeting, &n);
    printf("wifi_ssid=%s\ncontroller_url=%s\nmeeting_id=%s\n", ssid, controller, meeting);
    nvs_close(h);
    return ESP_OK;
}

static int cmd_led(int argc, char **argv) {
    if (argc != 2) {
        printf("usage: led <idle|notice|error|off>\n");
        return ESP_ERR_INVALID_ARG;
    }
    return status_led_set_pattern_name(argv[1]);
}

/* Bench check for the INMP441: capture ~1 s and print RMS / peak. A quiet room
 * should show a small non-zero RMS; clap near the mic and peak should jump. */
static int cmd_mic(int argc, char **argv) {
    (void)argc; (void)argv;
    static uint8_t frame[EFMA_BYTES_PER_FRAME];
    double sum_sq = 0;
    int peak = 0;
    const int frames = 50; /* 50 x 20 ms = 1 s */
    int got = 0;
    for (int i = 0; i < frames; i++) {
        if (audio_capture_read_frame(frame, sizeof(frame)) != ESP_OK) {
            continue;
        }
        got++;
        const int16_t *s = (const int16_t *)frame;
        for (int j = 0; j < EFMA_SAMPLES_PER_FRAME; j++) {
            int v = s[j];
            sum_sq += (double)v * v;
            if (v < 0) v = -v;
            if (v > peak) peak = v;
        }
    }
    if (got == 0) {
        printf("mic: capture failed (driver not ready?)\n");
        return ESP_FAIL;
    }
    double rms = sqrt(sum_sq / (got * EFMA_SAMPLES_PER_FRAME));
    printf("mic: %d/%d frames, rms=%.1f peak=%d (s16 full scale 32767), rx_isr=%lu ovf=%lu\n",
           got, frames, rms, peak, (unsigned long)audio_capture_debug_isr_count(),
           (unsigned long)audio_capture_debug_ovf_count());
    return ESP_OK;
}

/* Move the yaw servo: servo <head_deg> — head range is clamped to the
 * DeviceHello limits (±45 deg; the 2:1 belt maps to ±90 deg servo travel). */
static int cmd_servo(int argc, char **argv) {
    if (argc != 2) {
        printf("usage: servo <head_deg -45..45>\n");
        return ESP_ERR_INVALID_ARG;
    }
    char *end = NULL;
    float deg = strtof(argv[1], &end);
    if (!end || *end != '\0') {
        printf("usage: servo <head_deg -45..45>\n");
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t rc = servo_yaw_move_to(deg, 0);
    printf("servo: head %.1f deg -> rc=%s\n", (double)deg, esp_err_to_name(rc));
    return rc;
}

/* Measure I2S DMA completion rate: expect ~50 descriptors/s on each channel
 * (20 ms per descriptor at 16 kHz). Much lower = clock misconfigured. */
static int cmd_i2srate(int argc, char **argv) {    (void)argc; (void)argv;
    uint32_t rx0 = audio_capture_debug_isr_count();
    uint32_t tx0 = audio_playback_debug_isr_count();
    vTaskDelay(pdMS_TO_TICKS(1000));
    uint32_t rx1 = audio_capture_debug_isr_count();
    uint32_t tx1 = audio_playback_debug_isr_count();
    printf("i2srate: rx=%lu/s tx=%lu/s (expect ~50/s each)\n",
           (unsigned long)(rx1 - rx0), (unsigned long)(tx1 - tx0));
    return ESP_OK;
}

/* Bench uplink: stream mic frames to the relay until the server closes the
 * session (~40 s cap in media.py). The session must be bound first:
 *   POST /api/bench/meetings/{mid}/audio/bind  (operator, same config JSON)
 * then:  uplink <session_id> <stream_id> <stream_key>                        */
typedef struct {
    char session_id[40];
    char stream_id[132];
    uint32_t stream_key;
} uplink_args_t;

static void uplink_task(void *arg) {
    uplink_args_t *a = (uplink_args_t *)arg;
    device_session_t *s = device_session_active();
    if (!s) {
        printf("uplink: no active device session (not paired / no network?)\n");
    } else {
        esp_err_t rc = device_session_run_uplink(s, a->session_id, a->stream_id,
                                                 a->stream_key, "completed");
        printf("uplink: session ended, rc=%s\n", esp_err_to_name(rc));
    }
    free(a);
    vTaskDelete(NULL);
}

static int cmd_uplink(int argc, char **argv) {
    if (argc != 4) {
        printf("usage: uplink <session_id> <stream_id> <stream_key>\n");
        return ESP_ERR_INVALID_ARG;
    }
    uplink_args_t *a = calloc(1, sizeof(*a));
    if (!a) {
        return ESP_ERR_NO_MEM;
    }
    strncpy(a->session_id, argv[1], sizeof(a->session_id) - 1);
    strncpy(a->stream_id, argv[2], sizeof(a->stream_id) - 1);
    a->stream_key = (uint32_t)strtoul(argv[3], NULL, 10);
    if (xTaskCreate(uplink_task, "uplink", 8192, a, 4, NULL) != pdTRUE) {
        free(a);
        return ESP_ERR_NO_MEM;
    }
    printf("uplink: started (runs until the server closes, ~40 s max)\n");
    return ESP_OK;
}

/* Bench check for the MAX98357A: play a sine beep. */static int cmd_tone(int argc, char **argv) {
    int freq = (argc > 1) ? atoi(argv[1]) : 880;
    int ms = (argc > 2) ? atoi(argv[2]) : 500;
    if (freq <= 0 || freq > 8000 || ms <= 0 || ms > 5000) {
        printf("usage: tone [freq_hz 1-8000] [ms 1-5000]\n");
        return ESP_ERR_INVALID_ARG;
    }
    static uint8_t frame[EFMA_BYTES_PER_FRAME];
    if (audio_playback_begin() != ESP_OK) {
        printf("tone: playback driver not ready\n");
        return ESP_FAIL;
    }
    int total = EFMA_SAMPLE_RATE_HZ * ms / 1000;
    for (int done = 0; done < total; done += EFMA_SAMPLES_PER_FRAME) {
        int16_t *s = (int16_t *)frame;
        for (int j = 0; j < EFMA_SAMPLES_PER_FRAME; j++) {
            float t = (float)(done + j) / EFMA_SAMPLE_RATE_HZ;
            s[j] = (int16_t)(sinf(2.0f * (float)M_PI * freq * t) * 12000.0f);
        }
        audio_playback_write(frame, sizeof(frame));
    }
    audio_playback_end();
    printf("tone: %d Hz %d ms done, tx_isr=%lu ovf=%lu\n", freq, ms,
           (unsigned long)audio_playback_debug_isr_count(),
           (unsigned long)audio_playback_debug_ovf_count());
    return ESP_OK;
}


/* Bench check for the ILI9341: bars / backlight / solid fill. */
static int cmd_lcd(int argc, char **argv) {
    if (argc >= 2 && strcmp(argv[1], "off") == 0) {
        lcd_backlight(false);
        printf("lcd: backlight off\n");
        return ESP_OK;
    }
    if (argc >= 2 && strcmp(argv[1], "on") == 0) {
        lcd_backlight(true);
        printf("lcd: backlight on\n");
        return ESP_OK;
    }
    if (argc >= 5 && strcmp(argv[1], "fill") == 0) {
        int r = atoi(argv[2]), g = atoi(argv[3]), b = atoi(argv[4]);
        uint16_t c = (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
        lcd_fill(c);
        printf("lcd: fill rgb(%d,%d,%d)\n", r, g, b);
        return ESP_OK;
    }
    lcd_test_pattern();
    printf("lcd: color bars (usage: lcd [bars|on|off|fill <r> <g> <b>])\n");
    return ESP_OK;
}

esp_err_t provision_start(void) {
    esp_console_repl_t *repl = NULL;
    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "effmeet> ";
    repl_config.task_stack_size = 4096;
    esp_console_dev_uart_config_t hw_config = ESP_CONSOLE_DEV_UART_CONFIG_DEFAULT();
    esp_err_t rc = esp_console_new_repl_uart(&hw_config, &repl_config, &repl);
    if (rc != ESP_OK) {
        return rc;
    }
    esp_console_register_help_command();
    static const esp_console_cmd_t provision_cmd = {
        .command = "provision",
        .help = "provision <ssid> <pass> <controller_url> <meeting_id> <media_token>",
        .func = &cmd_provision,
    };
    static const esp_console_cmd_t status_cmd = {
        .command = "provision_status",
        .help = "show provisioned fields (no secrets)",
        .func = &cmd_provision_status,
    };
    static const esp_console_cmd_t led_cmd = {
        .command = "led",
        .help = "led <idle|notice|error|off>",
        .func = &cmd_led,
    };
    static const esp_console_cmd_t mic_cmd = {
        .command = "mic",
        .help = "capture 1 s from the mic, print RMS/peak",
        .func = &cmd_mic,
    };
    static const esp_console_cmd_t tone_cmd = {
        .command = "tone",
        .help = "tone [freq_hz] [ms] - play a sine beep on the amp",
        .func = &cmd_tone,
    };
    static const esp_console_cmd_t rate_cmd = {
        .command = "i2srate",
        .help = "measure I2S DMA completion rate over 1 s",
        .func = &cmd_i2srate,
    };
    static const esp_console_cmd_t uplink_cmd = {
        .command = "uplink",
        .help = "uplink <session_id> <stream_id> <stream_key> - stream mic to relay (bench)",
        .func = &cmd_uplink,
    };
    static const esp_console_cmd_t servo_cmd = {
        .command = "servo",
        .help = "servo <head_deg -45..45> - move the yaw head",
        .func = &cmd_servo,
    };
    static const esp_console_cmd_t lcd_cmd = {
        .command = "lcd",
        .help = "lcd [bars|on|off|fill r g b] - ILI9341 test",
        .func = &cmd_lcd,
    };
    esp_console_cmd_register(&provision_cmd);
    esp_console_cmd_register(&status_cmd);
    esp_console_cmd_register(&led_cmd);
    esp_console_cmd_register(&mic_cmd);
    esp_console_cmd_register(&tone_cmd);
    esp_console_cmd_register(&rate_cmd);
    esp_console_cmd_register(&uplink_cmd);
    esp_console_cmd_register(&servo_cmd);
    esp_console_cmd_register(&lcd_cmd);
    rc = esp_console_start_repl(repl);
    if (rc != ESP_OK) {
        return rc;
    }
    ESP_LOGW(TAG, "provision REPL started; use 'provision' to write Wi-Fi/controller/token");
    return ESP_OK;
}
