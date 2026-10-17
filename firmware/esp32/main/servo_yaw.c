#include "servo_yaw.h"

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "servo_yaw";

static float clampf(float v, float lo, float hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

esp_err_t servo_yaw_init(void) {
    /* TODO(bring-up): ledc_timer_config(SERVO_LEDC_TIMER, SERVO_FREQ_HZ) +
     * ledc_channel_config(SERVO_LEDC_CHANNEL, SERVO_PWM_GPIO). Verify MG90S
     * 500-2500us pulse range and that motion does not brown-out/reset the board
     * (firmware README constraint: servo motion must not trigger a reset). */
    ESP_LOGW(TAG, "servo_yaw_init: NOT-VERIFIED stub, no PWM configured");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t servo_yaw_move_to(float yaw_deg, int duration_ms) {
    (void)duration_ms;
    float head = clampf(yaw_deg, (float)EFFMEET_YAW_MIN_DEG, (float)EFFMEET_YAW_MAX_DEG);
    float servo_deg = head * SERVO_RATIO; /* 2:1 reduction -> servo travel */
    /* Map servo_deg (-90..90) to pulse width (SERVO_MIN_US..SERVO_MAX_US). */
    float us = SERVO_MIN_US + (servo_deg + 90.0f) / 180.0f * (SERVO_MAX_US - SERVO_MIN_US);
    ESP_LOGI(TAG, "move head=%.1f deg -> servo=%.1f deg (%.0f us) [stub]", head, servo_deg, us);
    /* TODO(bring-up): ledc_set_duty from us, ramp over duration_ms, ledc_update_duty. */
    return ESP_ERR_NOT_SUPPORTED;
}

void servo_yaw_stop(void) {
    /* TODO(bring-up): halt any ramp and hold current position. */
    ESP_LOGI(TAG, "servo_yaw_stop: stub");
}

void servo_yaw_deinit(void) {
    /* TODO(bring-up): ledc_stop + detach channel. */
}
