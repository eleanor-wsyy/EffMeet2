/* audio_playback — I2S amplifier (MAX98357A) <- 16 kHz mono s16le EFMA payload.
 * Owns the "network sent != played" boundary: playback completion is attested by
 * the device only after the last frame is drained to the codec, which gates the
 * RobotReceipt(completed) in device_session.
 * Pin map in app_config.h is still NOT-VERIFIED against the physical wiring;
 * use the REPL `tone` command to bench it.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t audio_playback_init(void);
/* Called once before a playback burst (flushes stale DMA samples, amp on). */
esp_err_t audio_playback_begin(void);
/* Queue decoded PCM for playback. Drops the frame (ESP_ERR_TIMEOUT) rather than
 * stalling the WS receive task when the DMA backlog is full. */
esp_err_t audio_playback_write(const uint8_t *pcm, size_t len);
/* Block until the queued audio has physically drained, then disable the amp.
 * Only after this returns may the caller attest RobotReceipt(completed). */
esp_err_t audio_playback_end(void);
/* Immediate stop (RobotCommand action=stop): cancel queued audio now. */
void audio_playback_stop(void);
/* Bench diagnostics: how many DMA completions the TX ISR has seen. */
uint32_t audio_playback_debug_isr_count(void);
uint32_t audio_playback_debug_ovf_count(void);
void audio_playback_deinit(void);

#ifdef __cplusplus
}
#endif
