#include "aec_afe.h"

#include "esp_log.h"

static const char *TAG = "aec_afe";
static bool s_speaking = false; /* software playback-mutex proxy; NOT real VAD */

esp_err_t aec_afe_init(void) {
#if defined(CONFIG_EFFMEET_ENABLE_AFE)
    /* TODO(bring-up): afe_config_init(), afe_handle->create_from_config(),
     * set AEC mode, register the reference feed. Requires PSRAM. */
    ESP_LOGW(TAG, "AFE enabled in config but DSP not implemented (NOT-VERIFIED)");
    return ESP_ERR_NOT_SUPPORTED;
#else
    ESP_LOGW(TAG, "AFE disabled; only software pause/playback mutex is active");
    return ESP_ERR_NOT_SUPPORTED;
#endif
}

esp_err_t aec_afe_set_reference(const uint8_t *pcm, size_t len) {
    (void)pcm; (void)len;
    /* TODO(bring-up): afe_handle->feed() the echo reference ring. */
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t aec_afe_process(uint8_t *frame, size_t len, size_t *out_len) {
    (void)frame; (void)len; (void)out_len;
    /* TODO(bring-up): afe_handle->fetch() cleaned audio. */
    return ESP_ERR_NOT_SUPPORTED;
}

bool aec_afe_quiet_moment(void) {
    /* Stub: NOT calibrated VAD/AEC. Replace with a real double-talk/VAD decision
     * before claiming the robot can listen while speaking. */
    return !s_speaking;
}

void aec_afe_set_speaking(bool speaking) {
    s_speaking = speaking;
}

void aec_afe_deinit(void) {
    /* TODO(bring-up): afe_handle->destroy(). */
}
