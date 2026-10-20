/* audio_capture — I2S microphone (INMP441) -> 16 kHz mono s16le 20 ms frames.
 * Feeds the EFMA uplink. When CONFIG_EFFMEET_ENABLE_AFE is set, raw mic frames
 * go through aec_afe first (echo cancellation + NS + VAD).
 * Pin map in app_config.h is still NOT-VERIFIED against the physical wiring;
 * use the REPL `mic` command to bench it.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t audio_capture_init(void);
/* Read exactly one 640-byte (320-sample, 20 ms) frame. Blocks up to ~4x frame
 * time; returns ESP_FAIL on a short read. */
esp_err_t audio_capture_read_frame(uint8_t *out, size_t out_cap);
/* Bench diagnostics: how many DMA completions the RX ISR has seen. */
uint32_t audio_capture_debug_isr_count(void);
uint32_t audio_capture_debug_ovf_count(void);
void audio_capture_deinit(void);

#ifdef __cplusplus
}
#endif
