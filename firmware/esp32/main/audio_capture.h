/* audio_capture — I2S microphone (INMP441) -> 16 kHz mono s16le 20 ms frames.
 * Feeds the EFMA uplink. When CONFIG_EFFMEET_ENABLE_AFE is set, raw mic frames
 * go through aec_afe first (echo cancellation + NS + VAD).
 * NOT-VERIFIED: no I2S peripheral has been initialized or sampled on hardware.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t audio_capture_init(void);
/* Read exactly one 640-byte (320-sample, 20 ms) frame. Blocks up to ~frame time.
 * Returns ESP_ERR_NOT_SUPPORTED until the I2S/AFE path is implemented. */
esp_err_t audio_capture_read_frame(uint8_t *out, size_t out_cap);
void audio_capture_deinit(void);

#ifdef __cplusplus
}
#endif
