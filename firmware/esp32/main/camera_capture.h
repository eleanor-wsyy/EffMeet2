/* camera_capture — JPEG snapshot for the capture/viewpoint evidence path.
 * The controller already accepts multipart capture upload + qwen3-vl-plus vision
 * (services/controller/app.py, README 10-05). This module produces the JPEG;
 * upload reuses the device HTTP path (out of scope for the WS media flows).
 * NOT-VERIFIED: camera model/pins are TBD; no sensor has been initialized.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t camera_capture_init(void);
/* Capture one JPEG into a caller buffer. Returns ESP_ERR_NOT_SUPPORTED until the
 * sensor + pin map are finalized. */
esp_err_t camera_capture_jpeg(uint8_t *out, size_t out_cap, size_t *out_len);
void camera_capture_deinit(void);

#ifdef __cplusplus
}
#endif
