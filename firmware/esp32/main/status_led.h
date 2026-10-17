/* status_led — single WS2812 pixel showing robot state.
 * Patterns map to RobotCommand action=light "pattern" enum: idle|notice|error|off.
 * NOT-VERIFIED: no LED has been driven; color order (GRB vs RGB) unconfirmed.
 */
#pragma once
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LED_PATTERN_IDLE = 0,
    LED_PATTERN_NOTICE,
    LED_PATTERN_ERROR,
    LED_PATTERN_OFF,
} led_pattern_t;

esp_err_t status_led_init(void);
esp_err_t status_led_set_pattern(led_pattern_t pattern);
/* Accepts the contract enum name ("idle"|"notice"|"error"|"off"). */
esp_err_t status_led_set_pattern_name(const char *name);
void status_led_deinit(void);

#ifdef __cplusplus
}
#endif
