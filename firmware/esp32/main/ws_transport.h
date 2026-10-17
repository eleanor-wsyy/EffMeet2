/* WebSocket transport for the two device endpoints in services/relay/media.py:
 *   uplink   WS /device/v1/audio     (mic PCM -> server, EFMA frames)
 *   playback WS /device/v1/playback  (server TTS PCM -> speaker, EFMA frames)
 *
 * Auth: "Authorization: Bearer <media_token>" header only. The relay accepts
 * loopback clients with no Origin and no query params, so the token MUST go in
 * the header, never the URL (matches media.py bearer()/local()).
 *
 * NOT-VERIFIED: written against esp_websocket_client (ESP-IDF v5.x) API shape
 * but never compiled/flashed here. Confirm the event/op_code fields against the
 * pinned IDF version at bring-up.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    WS_EVT_CONNECTED = 0,
    WS_EVT_DISCONNECTED,
    WS_EVT_TEXT,   /* JSON control message from server */
    WS_EVT_BINARY, /* EFMA frame from server (playback downlink) */
    WS_EVT_ERROR,
} ws_evt_type_t;

typedef struct {
    ws_evt_type_t type;
    const char *text;   /* valid for WS_EVT_TEXT (NUL-terminated copy) */
    const uint8_t *bin; /* valid for WS_EVT_BINARY */
    size_t len;
} ws_event_t;

typedef void (*ws_event_cb_t)(void *ctx, const ws_event_t *evt);

typedef struct ws_transport ws_transport_t;

/* Build a ws(s):// URI from an http(s):// base URL + path.
 * Returns ESP_OK on success. NOT-VERIFIED URL parsing. */
esp_err_t ws_build_uri(const char *scheme, const char *base_url, const char *path,
                       char *out, size_t out_cap);

/* Create a transport. bearer_token may be NULL only for pre-pairing probes.
 * The returned handle is owned by the caller; destroy with ws_transport_destroy. */
ws_transport_t *ws_transport_create(const char *uri, const char *bearer_token,
                                    ws_event_cb_t cb, void *ctx);
esp_err_t ws_transport_start(ws_transport_t *t);
bool ws_transport_is_connected(ws_transport_t *t);
esp_err_t ws_transport_send_text(ws_transport_t *t, const char *json);
esp_err_t ws_transport_send_bin(ws_transport_t *t, const uint8_t *data, size_t len);
void ws_transport_stop(ws_transport_t *t);
void ws_transport_destroy(ws_transport_t *t);

#ifdef __cplusplus
}
#endif
