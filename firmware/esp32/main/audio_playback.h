/* audio_playback — I2S amplifier (MAX98357A) <- 16 kHz mono s16le EFMA payload.
 * Owns the "network sent != played" boundary: playback completion is attested by
 * the device only after the last frame is drained to the codec, which gates the
 * RobotReceipt(completed) in device_session.
 * NOT-VERIFIED: no I2S output has been driven on hardware.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t audio_playback_init(void);
/* Called once before a playback burst (enables the amp / clears the ring). */
esp_err_t audio_playback_begin(void);
/* Queue decoded PCM for playback. Returns ESP_ERR_NOT_SUPPORTED until implemented. */
esp_err_t audio_playback_write(const uint8_t *pcm, size_t len);
/* Block until the queued audio has physically drained, then disable the amp.
 * Only after this returns may the caller attest RobotReceipt(completed). */
esp_err_t audio_playback_end(void);
/* Immediate stop (RobotCommand action=stop): cancel queued audio now. */
void audio_playback_stop(void);
void audio_playback_deinit(void);

#ifdef __cplusplus
}
#endif
