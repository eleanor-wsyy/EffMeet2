/* device_session — orchestrates the device-side protocol against the relay.
 *
 * Flows implemented to match services/relay/media.py and contracts/v1:
 *  - Pairing: operator POSTs /api/v1/meetings/{mid}/devices/{device_id}/pair and
 *    provisions the returned media_token into NVS. The device never pairs itself.
 *  - DeviceHello: {device_id, boot_id, capabilities[], limits{yaw_min_deg,yaw_max_deg}}.
 *  - Uplink  (/device/v1/audio):    AudioStreamConfig -> audio.ready -> EFMA frames
 *                                   (each acked) -> AudioStreamEnd -> audio.closed.
 *  - Playback(/device/v1/playback): hello{command_id,device_id,boot_id,safe_pause,
 *                                   sink_mode} -> audio.start -> AudioStreamReady ->
 *                                   RobotReceipt accepted -> started -> EFMA frames
 *                                   (device acks each) -> audio.end -> RobotReceipt
 *                                   completed -> playback.closed.
 *  - RobotCommand dispatch: orient|light|speak|stop.
 *
 * OPEN INTEGRATION POINT (NOT-VERIFIED): how a queued command_id reaches the
 * device. The local bench drives the player from the host side; a real robot
 * needs a command-delivery channel (e.g. subscribe to the controller events WS
 * and filter robot command.queued for this device_id). device_session_on_command()
 * is the intake seam; wiring the delivery transport is a bring-up task.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

/* NVS namespace for device identity and provisioning. */
#define EFFMEET_NVS_NAMESPACE "effmeet"

#ifdef __cplusplus
extern "C" {
#endif

/* RobotReceipt.status, per contracts/v1 RobotReceipt enum. */
typedef enum {
    RECEIPT_ACCEPTED = 0,
    RECEIPT_STARTED,
    RECEIPT_COMPLETED,
    RECEIPT_FAILED,
    RECEIPT_REJECTED,
} receipt_status_t;

typedef struct {
    char device_id[64];
    char boot_id[37];      /* UUID string, regenerated each boot */
    char meeting_id[37];
    char media_token[64];  /* from NVS; Bearer credential, never logged */
    char controller_url[128];
    char ws_scheme[8];     /* "ws" or "wss" */
    char wifi_ssid[64];    /* NVS first, Kconfig fallback; never log the pass */
    char wifi_pass[64];
    bool paired;           /* media_token present and bound */
    int  yaw_min_deg;
    int  yaw_max_deg;
} device_identity_t;

typedef struct device_session device_session_t;

/* Load identity + media_token from NVS (paired beforehand). Generates boot_id.
 * Returns ESP_ERR_NOT_FOUND if the device has not been paired yet. */
esp_err_t device_session_load_identity(device_identity_t *ident);

device_session_t *device_session_create(const device_identity_t *ident);
void device_session_destroy(device_session_t *s);

/* Build the DeviceHello JSON into out (NUL-terminated). */
esp_err_t device_session_hello_json(const device_session_t *s, char *out, size_t cap);

/* Run one uplink capture session: open WS, stream `frames` EFMA frames from the
 * mic path, then end with reason. Blocking; intended to run in its own task.
 * NOT-VERIFIED end to end. */
esp_err_t device_session_run_uplink(device_session_t *s, const char *session_id,
                                    const char *stream_id, uint32_t stream_key,
                                    const char *end_reason);

/* The single live session (set by device_session_create), for the REPL
 * `uplink` bench command. NULL before the session task starts. */
device_session_t *device_session_active(void);

/* Run the playback handshake for a queued command_id (speak action).
 * safe_pause must be true only when the device has attested a quiet moment
 * (media.py SAFE_PAUSE_REQUIRED). NOT-VERIFIED end to end. */
esp_err_t device_session_run_playback(device_session_t *s, const char *command_id,
                                      bool safe_pause, const char *sink_mode);

/* Subscribe to the controller events WS and dispatch robot commands for this
 * device. Uses the events WS hello {device_id,token,after_seq}; reconnects on
 * disconnect. NOT-VERIFIED until a real room is used. */
esp_err_t device_session_subscribe_commands(device_session_t *s);

/* Command intake seam: parse a RobotCommand JSON and dispatch orient/light/stop
 * directly, or trigger playback for speak. Returns ESP_OK if handled. */
esp_err_t device_session_on_command(device_session_t *s, const char *command_json);

/* Send a RobotReceipt for a command over an open playback transport. */
esp_err_t device_session_send_receipt(device_session_t *s, const char *command_id,
                                      receipt_status_t status, const char *error_code);

#ifdef __cplusplus
}
#endif
