/* Central board config + pin map for the EffMeet2 robot scaffold.
 *
 * NOT-VERIFIED: the ESP32-S3 board model is TBD (firmware/esp32/README.md) and
 * no pin below has been checked against a real board or the electrical BOM.
 * Treat every GPIO as a placeholder to reconcile with hardware/electronics/
 * wiring before bring-up. Do not claim any peripheral works until bench-tested.
 */
#pragma once

#include "sdkconfig.h"

/* ---- Identity / network (non-secret defaults; secrets come from NVS) ---- */
#define EFFMEET_DEVICE_ID        CONFIG_EFFMEET_DEVICE_ID
#define EFFMEET_CONTROLLER_URL   CONFIG_EFFMEET_CONTROLLER_URL
#define EFFMEET_WS_SCHEME        CONFIG_EFFMEET_WS_SCHEME
#define EFFMEET_WIFI_SSID        CONFIG_EFFMEET_WIFI_SSID
#define EFFMEET_WIFI_PASS        CONFIG_EFFMEET_WIFI_PASS

/* Device endpoints, matching services/relay/media.py exactly. */
#define EFFMEET_WS_UPLINK_PATH   "/device/v1/audio"
#define EFFMEET_WS_PLAYBACK_PATH "/device/v1/playback"

/* ---- Audio format: fixed by contracts/v1 AudioStreamConfig ---- */
#define EFMA_SAMPLE_RATE_HZ  16000
#define EFMA_CHANNELS        1
#define EFMA_FRAME_MS        20
#define EFMA_SAMPLES_PER_FRAME (EFMA_SAMPLE_RATE_HZ * EFMA_FRAME_MS / 1000) /* 320 */
#define EFMA_BYTES_PER_FRAME   (EFMA_SAMPLES_PER_FRAME * 2)                 /* 640 */

/* ---- I2S microphone (INMP441) — placeholder pins, NOT-VERIFIED ---- */
#define MIC_I2S_NUM        I2S_NUM_0
#define MIC_I2S_BCLK_GPIO  4
#define MIC_I2S_WS_GPIO    5
#define MIC_I2S_DIN_GPIO   6

/* ---- I2S amplifier (MAX98357A) — placeholder pins, NOT-VERIFIED ---- */
#define AMP_I2S_NUM        I2S_NUM_1
#define AMP_I2S_BCLK_GPIO  15
#define AMP_I2S_WS_GPIO    16
#define AMP_I2S_DOUT_GPIO  17
#define AMP_ENABLE_GPIO    18   /* optional SD/EN gate; -1 if not wired */

/* ---- Yaw servo (MG90S, 2:1 GT2 -> head +/-45 deg) — NOT-VERIFIED ---- */
#define SERVO_LEDC_TIMER   LEDC_TIMER_0
#define SERVO_LEDC_CHANNEL LEDC_CHANNEL_0
#define SERVO_PWM_GPIO     38
#define SERVO_FREQ_HZ      50    /* standard hobby servo frame */
#define SERVO_MIN_US       500
#define SERVO_MAX_US       2500
/* Servo sweeps +/-90 deg; the 2:1 belt reduces head travel to +/-45 deg. */
#define SERVO_RATIO        2.0f

/* ---- Status LED (WS2812 single pixel) — NOT-VERIFIED ---- */
#define LED_STRIP_GPIO     48
#define LED_STRIP_PIXELS   1

/* ---- LCD (2.8" ILI9341 SPI 240x320) — pins fixed on bench 2026-10-21 ---- */
#define LCD_CS_GPIO        10
#define LCD_DC_GPIO        9
#define LCD_RST_GPIO       14
#define LCD_MOSI_GPIO      11
#define LCD_SCLK_GPIO      12
#define LCD_BL_GPIO        47

/* ---- Camera (JPEG snapshot) — model/pins TBD, NOT-VERIFIED ---- */
/* Pin map intentionally omitted: fill from the finalized camera board. */

/* ---- Yaw limits reported in DeviceHello.limits ---- */
#define EFFMEET_YAW_MIN_DEG CONFIG_EFFMEET_YAW_MIN_DEG
#define EFFMEET_YAW_MAX_DEG CONFIG_EFFMEET_YAW_MAX_DEG
