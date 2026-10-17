/* servo_yaw — single-axis head yaw via MG90S over LEDC PWM.
 * Mechanical reduction is 2:1 (32T->64T GT2), so servo +/-90 deg maps to head
 * +/-45 deg (hardware/robot-design). RobotCommand action=orient carries yaw_deg
 * in HEAD space; this module converts to servo space and clamps to limits.
 * NOT-VERIFIED: no PWM has been driven; reduction ratio + limits unconfirmed.
 */
#pragma once
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t servo_yaw_init(void);
/* Move the head to yaw_deg (head space) over duration_ms. Clamps to
 * [EFFMEET_YAW_MIN_DEG, EFFMEET_YAW_MAX_DEG]. */
esp_err_t servo_yaw_move_to(float yaw_deg, int duration_ms);
void servo_yaw_stop(void);
void servo_yaw_deinit(void);

#ifdef __cplusplus
}
#endif
