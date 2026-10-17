/* ws_transport implementation over esp_websocket_client. NOT-VERIFIED (uncompiled).
 * Keep the token in the Authorization header; the relay rejects query params and
 * browser Origin for device endpoints (services/relay/media.py: bearer()/local()).
 */
#include "ws_transport.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "esp_log.h"
#include "esp_websocket_client.h"

static const char *TAG = "ws_transport";

struct ws_transport {
    esp_websocket_client_handle_t client;
    ws_event_cb_t cb;
    void *ctx;
    char *auth_header; /* persists for client lifetime */
};

esp_err_t ws_build_uri(const char *scheme, const char *base_url, const char *path,
                       char *out, size_t out_cap) {
    if (!scheme || !base_url || !path || !out) {
        return ESP_ERR_INVALID_ARG;
    }
    /* Strip an existing http(s):// or ws(s):// prefix from base_url. */
    const char *host = base_url;
    const char *sep = strstr(base_url, "://");
    if (sep) {
        host = sep + 3;
    }
    int n = snprintf(out, out_cap, "%s://%s%s", scheme, host, path);
    if (n < 0 || (size_t)n >= out_cap) {
        return ESP_ERR_INVALID_SIZE;
    }
    return ESP_OK;
}

static void on_ws_event(void *arg, esp_event_base_t base, int32_t event_id, void *event_data) {
    ws_transport_t *t = (ws_transport_t *)arg;
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    (void)base;
    if (!t || !t->cb) {
        return;
    }
    ws_event_t evt = {0};
    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            evt.type = WS_EVT_CONNECTED;
            t->cb(t->ctx, &evt);
            break;
        case WEBSOCKET_EVENT_DISCONNECTED:
            evt.type = WS_EVT_DISCONNECTED;
            t->cb(t->ctx, &evt);
            break;
        case WEBSOCKET_EVENT_ERROR:
            evt.type = WS_EVT_ERROR;
            t->cb(t->ctx, &evt);
            break;
        case WEBSOCKET_EVENT_DATA:
            /* op_code 0x1 = text (JSON control), 0x2 = binary (EFMA frame). */
            if (data->op_code == 0x02) {
                evt.type = WS_EVT_BINARY;
                evt.bin = (const uint8_t *)data->data_ptr;
                evt.len = (size_t)data->data_len;
                t->cb(t->ctx, &evt);
            } else if (data->op_code == 0x01 && data->data_ptr && data->data_len > 0) {
                /* Copy to a NUL-terminated buffer for the JSON layer. */
                size_t n = (size_t)data->data_len;
                char *buf = (char *)malloc(n + 1);
                if (buf) {
                    memcpy(buf, data->data_ptr, n);
                    buf[n] = '\0';
                    evt.type = WS_EVT_TEXT;
                    evt.text = buf;
                    evt.len = n;
                    t->cb(t->ctx, &evt);
                    free(buf);
                }
            }
            break;
        default:
            break;
    }
}

ws_transport_t *ws_transport_create(const char *uri, const char *bearer_token,
                                    ws_event_cb_t cb, void *ctx) {
    if (!uri) {
        return NULL;
    }
    ws_transport_t *t = (ws_transport_t *)calloc(1, sizeof(*t));
    if (!t) {
        return NULL;
    }
    t->cb = cb;
    t->ctx = ctx;
    if (bearer_token && bearer_token[0]) {
        size_t hlen = strlen(bearer_token) + 32;
        t->auth_header = (char *)malloc(hlen);
        if (!t->auth_header) {
            free(t);
            return NULL;
        }
        snprintf(t->auth_header, hlen, "Authorization: Bearer %s\r\n", bearer_token);
    }
    esp_websocket_client_config_t cfg = {0};
    cfg.uri = uri;
    cfg.headers = t->auth_header; /* NULL is allowed by the client */
    cfg.buffer_size = 8192;       /* >= EFMA_MAX_DECODED control + frame headroom */
    cfg.network_timeout_ms = 10000;
    t->client = esp_websocket_client_init(&cfg);
    if (!t->client) {
        free(t->auth_header);
        free(t);
        return NULL;
    }
    esp_websocket_client_register_events(t->client, WEBSOCKET_EVENT_ANY, on_ws_event, t);
    return t;
}

esp_err_t ws_transport_start(ws_transport_t *t) {
    if (!t || !t->client) {
        return ESP_ERR_INVALID_ARG;
    }
    return esp_websocket_client_start(t->client);
}

bool ws_transport_is_connected(ws_transport_t *t) {
    return t && t->client && esp_websocket_client_is_connected(t->client);
}

esp_err_t ws_transport_send_text(ws_transport_t *t, const char *json) {
    if (!t || !t->client || !json) {
        return ESP_ERR_INVALID_ARG;
    }
    int sent = esp_websocket_client_send_text(t->client, json, (int)strlen(json),
                                              pdMS_TO_TICKS(5000));
    return sent >= 0 ? ESP_OK : ESP_FAIL;
}

esp_err_t ws_transport_send_bin(ws_transport_t *t, const uint8_t *data, size_t len) {
    if (!t || !t->client || !data || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    int sent = esp_websocket_client_send_bin(t->client, (const char *)data, (int)len,
                                             pdMS_TO_TICKS(5000));
    return sent >= 0 ? ESP_OK : ESP_FAIL;
}

void ws_transport_stop(ws_transport_t *t) {
    if (t && t->client) {
        esp_websocket_client_stop(t->client);
    }
}

void ws_transport_destroy(ws_transport_t *t) {
    if (!t) {
        return;
    }
    if (t->client) {
        esp_websocket_client_destroy(t->client);
    }
    free(t->auth_header);
    free(t);
}
