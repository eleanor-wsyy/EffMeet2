/* audio_capture — INMP441 on I2S RX, 16 kHz mono s16le, 640-byte frames.
 *
 * The INMP441 emits 24-bit data left-justified in a 32-bit I2S slot, so the
 * channel runs at 32-bit slot width and each sample is truncated to s16 by
 * dropping the low 16 bits (>> 16; no gain, no clipping possible).
 * L/R select is assumed wired to GND (left slot); flip MIC_I2S_SLOT below if
 * the bench capture is silent.
 */
#include "audio_capture.h"

#include <string.h>

#include "aec_afe.h"
#include "app_config.h"
#include "driver/i2s_std.h"
#include "esp_attr.h"
#include "esp_log.h"

static const char *TAG = "audio_capture";

/* 8 descriptors x 320 frames: 40 ms of DMA, >= 1 EFMA frame of slack. */
#define MIC_DMA_DESC_NUM   8
#define MIC_DMA_FRAME_NUM  320
#define MIC_RAW_BYTES      (EFMA_SAMPLES_PER_FRAME * 4) /* 32-bit slots */

static i2s_chan_handle_t s_rx;

/* Diagnostics: count RX ISR completions (temporary, for bench bring-up). */
static volatile uint32_t s_rx_isr_count;

static bool IRAM_ATTR rx_on_recv(i2s_chan_handle_t handle, i2s_event_data_t *event,
                                 void *user_ctx) {
    s_rx_isr_count++;
    return false;
}

static volatile uint32_t s_rx_ovf_count;

static bool IRAM_ATTR rx_on_ovf(i2s_chan_handle_t handle, i2s_event_data_t *event,
                                void *user_ctx) {
    s_rx_ovf_count++;
    return false;
}

uint32_t audio_capture_debug_isr_count(void) {
    return s_rx_isr_count;
}

uint32_t audio_capture_debug_ovf_count(void) {
    return s_rx_ovf_count;
}

esp_err_t audio_capture_init(void) {
    i2s_chan_config_t chan = I2S_CHANNEL_DEFAULT_CONFIG(MIC_I2S_NUM, I2S_ROLE_MASTER);
    chan.dma_desc_num = MIC_DMA_DESC_NUM;
    chan.dma_frame_num = MIC_DMA_FRAME_NUM;
    esp_err_t rc = i2s_new_channel(&chan, NULL, &s_rx);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_new_channel(rx) failed: %s", esp_err_to_name(rc));
        return rc;
    }
    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(EFMA_SAMPLE_RATE_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = MIC_I2S_BCLK_GPIO,
            .ws = MIC_I2S_WS_GPIO,
            .dout = I2S_GPIO_UNUSED,
            .din = MIC_I2S_DIN_GPIO,
            .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
        },
    };
    std.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT; /* INMP441 L/R pin to GND */
    rc = i2s_channel_init_std_mode(s_rx, &std);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_channel_init_std_mode(rx) failed: %s", esp_err_to_name(rc));
        i2s_del_channel(s_rx);
        s_rx = NULL;
        return rc;
    }
    i2s_event_callbacks_t cbs = { .on_recv = rx_on_recv, .on_recv_q_ovf = rx_on_ovf };
    i2s_channel_register_event_callback(s_rx, &cbs, NULL);
    rc = i2s_channel_enable(s_rx);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_channel_enable(rx) failed: %s", esp_err_to_name(rc));
        i2s_del_channel(s_rx);
        s_rx = NULL;
        return rc;
    }
    ESP_LOGI(TAG, "I2S RX up: %d Hz mono, bclk=%d ws=%d din=%d",
             EFMA_SAMPLE_RATE_HZ, MIC_I2S_BCLK_GPIO, MIC_I2S_WS_GPIO, MIC_I2S_DIN_GPIO);
    return ESP_OK;
}

esp_err_t audio_capture_read_frame(uint8_t *out, size_t out_cap) {
    if (!out || out_cap < EFMA_BYTES_PER_FRAME) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!s_rx) {
        return ESP_ERR_INVALID_STATE;
    }
    int32_t raw[EFMA_SAMPLES_PER_FRAME];
    size_t got = 0;
    /* NOTE: i2s_channel_read takes milliseconds, NOT FreeRTOS ticks. */
    esp_err_t rc = i2s_channel_read(s_rx, raw, MIC_RAW_BYTES, &got,
                                    EFMA_FRAME_MS * 4);
    if (rc != ESP_OK || got < MIC_RAW_BYTES) {
        ESP_LOGW(TAG, "mic read short: rc=%s bytes=%u", esp_err_to_name(rc), (unsigned)got);
        return ESP_FAIL;
    }
    int16_t *pcm = (int16_t *)out;
    for (int i = 0; i < EFMA_SAMPLES_PER_FRAME; i++) {
        pcm[i] = (int16_t)(raw[i] >> 16);
    }
    return ESP_OK;
}

void audio_capture_deinit(void) {
    if (s_rx) {
        i2s_channel_disable(s_rx);
        i2s_del_channel(s_rx);
        s_rx = NULL;
    }
}
