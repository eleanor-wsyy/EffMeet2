/* audio_playback — MAX98357A on I2S TX, 16 kHz mono s16le.
 *
 * The TX channel stays enabled after init; the amp SD/EN pin gates audible
 * output. begin() disables+re-enables the channel to drop any samples left in
 * DMA by a previous burst (e.g. after stop()), so playback always starts clean.
 * end() is the attestation boundary: it waits out the worst-case DMA backlog
 * before gating the amp, so RobotReceipt(completed) never precedes real audio.
 */
#include "audio_playback.h"

#include "app_config.h"
#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "audio_playback";

/* 8 descriptors x 320 frames = 160 ms worst-case DMA backlog. */
#define AMP_DMA_DESC_NUM   8
#define AMP_DMA_FRAME_NUM  320
#define AMP_DRAIN_MS       (AMP_DMA_DESC_NUM * AMP_DMA_FRAME_NUM * 1000 / \
                            EFMA_SAMPLE_RATE_HZ + 50)
/* Writes may block at most this long before we drop the frame. */
#define AMP_WRITE_TIMEOUT_MS 100

static i2s_chan_handle_t s_tx;
static bool s_amp_on;

/* Diagnostics: count TX ISR completions (temporary, for bench bring-up). */
static volatile uint32_t s_tx_isr_count;

static bool IRAM_ATTR tx_on_sent(i2s_chan_handle_t handle, i2s_event_data_t *event,
                                 void *user_ctx) {
    s_tx_isr_count++;
    return false;
}

static volatile uint32_t s_tx_ovf_count;

static bool IRAM_ATTR tx_on_ovf(i2s_chan_handle_t handle, i2s_event_data_t *event,
                                void *user_ctx) {
    s_tx_ovf_count++;
    return false;
}

uint32_t audio_playback_debug_isr_count(void) {
    return s_tx_isr_count;
}

uint32_t audio_playback_debug_ovf_count(void) {
    return s_tx_ovf_count;
}

static void amp_drive(bool on) {
    if (AMP_ENABLE_GPIO >= 0) {
        gpio_set_level(AMP_ENABLE_GPIO, on ? 1 : 0);
    }
    s_amp_on = on;
}

esp_err_t audio_playback_init(void) {
    if (AMP_ENABLE_GPIO >= 0) {
        gpio_config_t io = {
            .pin_bit_mask = 1ULL << AMP_ENABLE_GPIO,
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io);
        gpio_set_level(AMP_ENABLE_GPIO, 0);
    }
    i2s_chan_config_t chan = I2S_CHANNEL_DEFAULT_CONFIG(AMP_I2S_NUM, I2S_ROLE_MASTER);
    chan.dma_desc_num = AMP_DMA_DESC_NUM;
    chan.dma_frame_num = AMP_DMA_FRAME_NUM;
    esp_err_t rc = i2s_new_channel(&chan, &s_tx, NULL);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_new_channel(tx) failed: %s", esp_err_to_name(rc));
        return rc;
    }
    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(EFMA_SAMPLE_RATE_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = AMP_I2S_BCLK_GPIO,
            .ws = AMP_I2S_WS_GPIO,
            .dout = AMP_I2S_DOUT_GPIO,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
        },
    };
    rc = i2s_channel_init_std_mode(s_tx, &std);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_channel_init_std_mode(tx) failed: %s", esp_err_to_name(rc));
        i2s_del_channel(s_tx);
        s_tx = NULL;
        return rc;
    }
    i2s_event_callbacks_t cbs = { .on_sent = tx_on_sent, .on_send_q_ovf = tx_on_ovf };
    i2s_channel_register_event_callback(s_tx, &cbs, NULL);
    rc = i2s_channel_enable(s_tx);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "i2s_channel_enable(tx) failed: %s", esp_err_to_name(rc));
        i2s_del_channel(s_tx);
        s_tx = NULL;
        return rc;
    }
    ESP_LOGI(TAG, "I2S TX up: %d Hz mono, bclk=%d ws=%d dout=%d en=%d",
             EFMA_SAMPLE_RATE_HZ, AMP_I2S_BCLK_GPIO, AMP_I2S_WS_GPIO,
             AMP_I2S_DOUT_GPIO, AMP_ENABLE_GPIO);
    return ESP_OK;
}

esp_err_t audio_playback_begin(void) {
    if (!s_tx) {
        return ESP_ERR_INVALID_STATE;
    }
    /* Flush any samples a stopped burst left in DMA. */
    i2s_channel_disable(s_tx);
    esp_err_t rc = i2s_channel_enable(s_tx);
    if (rc != ESP_OK) {
        return rc;
    }
    amp_drive(true);
    return ESP_OK;
}

esp_err_t audio_playback_write(const uint8_t *pcm, size_t len) {
    if (!pcm || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!s_tx) {
        return ESP_ERR_INVALID_STATE;
    }
    /* NOTE: i2s_channel_write takes milliseconds, NOT FreeRTOS ticks. */
    size_t written = 0;
    esp_err_t rc = i2s_channel_write(s_tx, pcm, len, &written,
                                     AMP_WRITE_TIMEOUT_MS);
    if (rc != ESP_OK || written < len) {
        /* Better to drop a frame than to stall the WS receive task; the caller
         * still acks, so the controller sees a continuous stream. */
        ESP_LOGW(TAG, "playback write dropped %u/%u bytes (rc=%s)",
                 (unsigned)(len - written), (unsigned)len, esp_err_to_name(rc));
        return ESP_ERR_TIMEOUT;
    }
    return ESP_OK;
}

esp_err_t audio_playback_end(void) {
    if (!s_tx) {
        return ESP_ERR_INVALID_STATE;
    }
    /* Wait out the worst-case DMA backlog: this is the "played" boundary. */
    vTaskDelay(pdMS_TO_TICKS(AMP_DRAIN_MS));
    amp_drive(false);
    return ESP_OK;
}

void audio_playback_stop(void) {
    if (!s_tx) {
        return;
    }
    amp_drive(false);
    i2s_channel_disable(s_tx);
    i2s_channel_enable(s_tx);
}

void audio_playback_deinit(void) {
    if (s_tx) {
        amp_drive(false);
        i2s_channel_disable(s_tx);
        i2s_del_channel(s_tx);
        s_tx = NULL;
    }
}
