#include "status_led.h"

#include <string.h>

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "status_led";

esp_err_t status_led_init(void) {
    /* TODO(bring-up): led_strip_new_rmt_device() on LED_STRIP_GPIO, LED_STRIP_PIXELS.
     * Confirm GRB vs RGB color order against the actual LED part. */
    ESP_LOGW(TAG, "status_led_init: NOT-VERIFIED stub, no LED configured");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t status_led_set_pattern(led_pattern_t pattern) {
    /* TODO(bring-up): map pattern to an animated/breathing sequence on a timer.
     * Placeholder logs only. */
    static const char *names[] = {"idle", "notice", "error", "off"};
    ESP_LOGI(TAG, "pattern=%s [stub]", names[pattern]);
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t status_led_set_pattern_name(const char *name) {
    if (!name) {
        return ESP_ERR_INVALID_ARG;
    }
    if (strcmp(name, "idle") == 0)   return status_led_set_pattern(LED_PATTERN_IDLE);
    if (strcmp(name, "notice") == 0) return status_led_set_pattern(LED_PATTERN_NOTICE);
    if (strcmp(name, "error") == 0)  return status_led_set_pattern(LED_PATTERN_ERROR);
    if (strcmp(name, "off") == 0)    return status_led_set_pattern(LED_PATTERN_OFF);
    return ESP_ERR_INVALID_ARG;
}

void status_led_deinit(void) {
    /* TODO(bring-up): led_strip_del(). */
}
