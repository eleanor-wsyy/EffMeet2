#include "camera_capture.h"

#include "esp_log.h"

static const char *TAG = "camera_capture";

esp_err_t camera_capture_init(void) {
    /* TODO(bring-up): finalize camera board (model + pin map), then esp_camera_init().
     * Keep JPEG quality/size within the controller 2 MiB upload limit. */
    ESP_LOGW(TAG, "camera_capture_init: NOT-VERIFIED stub, sensor TBD");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t camera_capture_jpeg(uint8_t *out, size_t out_cap, size_t *out_len) {
    (void)out; (void)out_cap; (void)out_len;
    /* TODO(bring-up): esp_camera_fb_get() -> copy JPEG -> esp_camera_fb_return(). */
    return ESP_ERR_NOT_SUPPORTED;
}

void camera_capture_deinit(void) {
    /* TODO(bring-up): esp_camera_deinit(). */
}
