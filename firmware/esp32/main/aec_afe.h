/* aec_afe — acoustic echo cancellation / audio front-end hook (route B goal:
 * "listen while speaking" without feeding the robot's own TTS back into ASR).
 *
 * This is the seam for ESP-SR AFE (AEC + NS + VAD). It needs three things the
 * current software-only pause/playback mutex does NOT provide:
 *   1. an echo reference channel (the exact PCM sent to the amp),
 *   2. delay alignment between reference and mic,
 *   3. double-talk handling (user speaks while robot speaks).
 *
 * NOT-VERIFIED: no DSP is implemented. aec_afe_quiet_moment() currently reports
 * "quiet" only from the software playback-mutex state, which is NOT calibrated
 * VAD/AEC (mirrors the SAFE_PAUSE_REQUIRED caveat in services/relay/media.py).
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t aec_afe_init(void);
/* Feed the echo reference (the PCM handed to audio_playback_write). */
esp_err_t aec_afe_set_reference(const uint8_t *pcm, size_t len);
/* Process one raw mic frame in place; returns cleaned frame length. */
esp_err_t aec_afe_process(uint8_t *frame, size_t len, size_t *out_len);
/* True when the front-end attests a quiet moment safe for playback.
 * Stub: derived from the playback mutex, NOT real VAD/AEC. */
bool aec_afe_quiet_moment(void);
/* Mark the software playback-mutex state (drives the quiet_moment stub). */
void aec_afe_set_speaking(bool speaking);
void aec_afe_deinit(void);

#ifdef __cplusplus
}
#endif
