#include "servo_yaw.h"

#include "app_config.h"
#include "driver/ledc.h"
#include "esp_log.h"

static const char *TAG = "servo_yaw";
static bool s_ready = false;

static float clampf(float v, float lo, float hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

static uint32_t us_to_duty(float us) {
    const float period_us = 1000000.0f / SERVO_FREQ_HZ;
    return (uint32_t)(us / period_us * ((1 << 13) - 1));
}

esp_err_t servo_yaw_init(void) {
    ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num = SERVO_LEDC_TIMER,
        .duty_resolution = LEDC_TIMER_13_BIT,
        .freq_hz = SERVO_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t rc = ledc_timer_config(&timer);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "ledc_timer_config failed: %s", esp_err_to_name(rc));
        return rc;
    }
    ledc_channel_config_t channel = {
        .gpio_num = SERVO_PWM_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = SERVO_LEDC_CHANNEL,
        .timer_sel = SERVO_LEDC_TIMER,
        .duty = 0,
        .hpoint = 0,
    };
    rc = ledc_channel_config(&channel);
    if (rc != ESP_OK) {
        ESP_LOGW(TAG, "ledc_channel_config failed: %s", esp_err_to_name(rc));
        return rc;
    }
    s_ready = true;
    return servo_yaw_move_to(0, 0);
}

esp_err_t servo_yaw_move_to(float yaw_deg, int duration_ms) {
    (void)duration_ms;  /* ramp control is a later refinement; set position now */
    if (!s_ready) {
        return ESP_ERR_INVALID_STATE;
    }
    float head = clampf(yaw_deg, (float)EFFMEET_YAW_MIN_DEG, (float)EFFMEET_YAW_MAX_DEG);
    float servo_deg = head * SERVO_RATIO;  /* 2:1 GT2 reduction */
    float us = SERVO_MIN_US + (servo_deg + 90.0f) / 180.0f * (SERVO_MAX_US - SERVO_MIN_US);
    uint32_t duty = us_to_duty(us);
    esp_err_t rc = ledc_set_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, duty);
    if (rc == ESP_OK) {
        rc = ledc_update_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL);
    }
    return rc;
}

void servo_yaw_stop(void) {
    if (s_ready) {
        ledc_stop(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, 0);
    }
}

void servo_yaw_deinit(void) {
    if (s_ready) {
        ledc_stop(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, 0);
        s_ready = false;
    }
}
