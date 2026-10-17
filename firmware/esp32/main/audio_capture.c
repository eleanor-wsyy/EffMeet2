#include "audio_capture.h"

#include "aec_afe.h"
#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "audio_capture";

esp_err_t audio_capture_init(void) {
    /* TODO(bring-up): configure I2S_NUM_0 in standard/Philips mode, 16 kHz, mono,
     * 16-bit, using MIC_I2S_* pins from app_config.h. Verify INMP441 timing
     * (L/R select to GND) against hardware/electronics wiring. If AFE enabled,
     * call aec_afe_init() and route raw frames through aec_afe_process(). */
    ESP_LOGW(TAG, "audio_capture_init: NOT-VERIFIED stub, no I2S configured");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t audio_capture_read_frame(uint8_t *out, size_t out_cap) {
    if (!out || out_cap < EFMA_BYTES_PER_FRAME) {
        return ESP_ERR_INVALID_ARG;
    }
    /* TODO(bring-up): i2s_channel_read() one 640-byte frame; if AFE enabled,
     * return aec_afe_process(raw) instead of raw mic data. */
    return ESP_ERR_NOT_SUPPORTED;
}

void audio_capture_deinit(void) {
    /* TODO(bring-up): disable + delete the I2S RX channel. */
}
