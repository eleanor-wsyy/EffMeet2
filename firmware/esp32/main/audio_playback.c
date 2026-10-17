#include "audio_playback.h"

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "audio_playback";

esp_err_t audio_playback_init(void) {
    /* TODO(bring-up): configure I2S_NUM_1 TX, 16 kHz mono 16-bit, AMP_I2S_* pins;
     * drive AMP_ENABLE_GPIO high. Verify MAX98357A SD/EN polarity against the
     * electrical BOM. */
    ESP_LOGW(TAG, "audio_playback_init: NOT-VERIFIED stub, no I2S configured");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t audio_playback_begin(void) {
    /* TODO(bring-up): enable amp, reset the playback ring buffer. */
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t audio_playback_write(const uint8_t *pcm, size_t len) {
    if (!pcm || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    /* TODO(bring-up): i2s_channel_write() into a bounded ring; never grow without
     * limit. Drop/flag on overflow rather than blocking the WS receive task. */
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t audio_playback_end(void) {
    /* TODO(bring-up): wait for the codec to drain the last sample (this is the
     * real "played" boundary), then disable the amp. */
    return ESP_ERR_NOT_SUPPORTED;
}

void audio_playback_stop(void) {
    /* TODO(bring-up): flush the ring immediately and disable the amp. */
    ESP_LOGI(TAG, "audio_playback_stop: stub");
}

void audio_playback_deinit(void) {
    /* TODO(bring-up): disable + delete the I2S TX channel. */
}
