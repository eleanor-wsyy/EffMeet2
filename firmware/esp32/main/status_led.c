#include "status_led.h"

#include <string.h>

#include "app_config.h"
#include "esp_log.h"
#include "led_strip.h"

static const char *TAG = "status_led";
static led_strip_handle_t s_strip = NULL;

/* Warm, low-brightness palette; never flash a bright error light into a meeting. */
static const uint8_t PALETTE[4][3] = {
    [LED_PATTERN_IDLE]   = {16, 8, 4},    /* dim warm */
    [LED_PATTERN_NOTICE] = {24, 10, 2},   /* coral */
    [LED_PATTERN_ERROR]  = {32, 0, 0},    /* red */
    [LED_PATTERN_OFF]    = {0, 0, 0},
};

esp_err_t status_led_init(void) {
    led_strip_config_t cfg = {
        .strip_gpio_num = LED_STRIP_GPIO,
        .max_leds = LED_STRIP_PIXELS,
        .led_pixel_format = LED_PIXEL_FORMAT_GRB,
        .led_model = LED_MODEL_WS2812,
        .flags.invert_out = false,
    };
    led_strip_rmt_config_t rmt = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
        .flags.with_dma = false,
    };
    esp_err_t rc = led_strip_new_rmt_device(&cfg, &rmt, &s_strip);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "status_led_init failed: %s", esp_err_to_name(rc));
        return rc;
    }
    return status_led_set_pattern(LED_PATTERN_IDLE);
}

esp_err_t status_led_set_pattern(led_pattern_t pattern) {
    if (!s_strip) {
        return ESP_ERR_INVALID_STATE;
    }
    if (pattern > LED_PATTERN_OFF) {
        return ESP_ERR_INVALID_ARG;
    }
    const uint8_t *rgb = PALETTE[pattern];
    esp_err_t rc = led_strip_set_pixel(s_strip, 0, rgb[0], rgb[1], rgb[2]);
    if (rc != ESP_OK) {
        return rc;
    }
    return led_strip_refresh(s_strip);
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
    if (s_strip) {
        led_strip_del(s_strip);
        s_strip = NULL;
    }
}
