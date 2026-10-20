/* device_session implementation. NOT-VERIFIED: uncompiled scaffold.
 *
 * The WS flows are callback-driven; each flow runs in its own task and pulls
 * received messages off a FreeRTOS queue. Timing, backpressure and the real
 * audio path need bench bring-up. Protocol shapes mirror media.py + contracts/v1.
 */
#include "device_session.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_log.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "aec_afe.h"
#include "app_config.h"
#include "audio_capture.h"
#include "audio_playback.h"
#include "efma_codec.h"
#include "servo_yaw.h"
#include "status_led.h"
#include "ws_transport.h"

static const char *TAG = "device_session";
#define NVS_NAMESPACE EFFMEET_NVS_NAMESPACE
#define RX_QUEUE_LEN 8
#define RX_TIMEOUT_MS 8000

struct device_session {
    device_identity_t ident;
    ws_transport_t *tx;        /* active transport for the current flow */
    ws_transport_t *events;    /* command subscription transport */
    QueueHandle_t rx;          /* rx_msg_t* from the WS callback */
    char playback_cmd[37];     /* command_id bound to the open playback WS */
    uint32_t after_seq;        /* last controller event seq seen */
    TaskHandle_t command_task;
};

typedef struct {
    ws_evt_type_t type;
    uint8_t *buf;
    size_t len;
} rx_msg_t;

static void rx_free(rx_msg_t *m) {
    if (m) {
        free(m->buf);
        free(m);
    }
}

static void on_ws(void *ctx, const ws_event_t *evt) {
    device_session_t *s = (device_session_t *)ctx;
    if (!s || !s->rx) {
        return;
    }
    rx_msg_t *m = (rx_msg_t *)calloc(1, sizeof(*m));
    if (!m) {
        return;
    }
    m->type = evt->type;
    if (evt->type == WS_EVT_TEXT && evt->text) {
        m->len = evt->len;
        m->buf = (uint8_t *)malloc(m->len + 1);
        if (m->buf) {
            memcpy(m->buf, evt->text, m->len);
            m->buf[m->len] = '\0';
        }
    } else if (evt->type == WS_EVT_BINARY && evt->bin) {
        m->len = evt->len;
        m->buf = (uint8_t *)malloc(m->len);
        if (m->buf) {
            memcpy(m->buf, evt->bin, m->len);
        }
    }
    if (xQueueSend(s->rx, &m, 0) != pdTRUE) {
        rx_free(m); /* drop on full queue; flow will time out and reset */
    }
}

static void make_boot_id(char out[37]) {
    uint32_t w[4] = {esp_random(), esp_random(), esp_random(), esp_random()};
    uint8_t *b = (uint8_t *)w;
    b[6] = (b[6] & 0x0F) | 0x40; /* version 4 */
    b[8] = (b[8] & 0x3F) | 0x80; /* variant */
    snprintf(out, 37,
             "%08" PRIx32 "-%04" PRIx32 "-%04" PRIx32 "-%04" PRIx32 "-%012" PRIx64,
             w[0], w[1] >> 16, w[1] & 0xFFFF, w[2] >> 16,
             ((uint64_t)(w[2] & 0xFFFF) << 32) | w[3]);
}

esp_err_t device_session_load_identity(device_identity_t *ident) {
    if (!ident) {
        return ESP_ERR_INVALID_ARG;
    }
    memset(ident, 0, sizeof(*ident));
    make_boot_id(ident->boot_id);
    strncpy(ident->device_id, EFFMEET_DEVICE_ID, sizeof(ident->device_id) - 1);
    strncpy(ident->controller_url, EFFMEET_CONTROLLER_URL, sizeof(ident->controller_url) - 1);
    strncpy(ident->ws_scheme, EFFMEET_WS_SCHEME, sizeof(ident->ws_scheme) - 1);
    strncpy(ident->wifi_ssid, EFFMEET_WIFI_SSID, sizeof(ident->wifi_ssid) - 1);
    strncpy(ident->wifi_pass, EFFMEET_WIFI_PASS, sizeof(ident->wifi_pass) - 1);
    ident->yaw_min_deg = EFFMEET_YAW_MIN_DEG;
    ident->yaw_max_deg = EFFMEET_YAW_MAX_DEG;

    nvs_handle_t h;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &h) != ESP_OK) {
        ESP_LOGW(TAG, "NVS namespace '%s' absent; using compile-time defaults", NVS_NAMESPACE);
        return ESP_OK;
    }
    size_t n;
    n = sizeof(ident->wifi_ssid);
    nvs_get_str(h, "wifi_ssid", ident->wifi_ssid, &n);
    n = sizeof(ident->wifi_pass);
    nvs_get_str(h, "wifi_pass", ident->wifi_pass, &n);
    n = sizeof(ident->controller_url);
    nvs_get_str(h, "controller_url", ident->controller_url, &n);
    n = sizeof(ident->meeting_id);
    esp_err_t e1 = nvs_get_str(h, "meeting_id", ident->meeting_id, &n);
    n = sizeof(ident->media_token);
    esp_err_t e2 = nvs_get_str(h, "media_token", ident->media_token, &n);
    nvs_close(h);
    ident->paired = (e1 == ESP_OK && e2 == ESP_OK && ident->media_token[0] != '\0');
    if (!ident->paired) {
        ESP_LOGW(TAG, "no paired media_token in NVS; run operator pairing first");
    }
    return ESP_OK;
}

device_session_t *device_session_create(const device_identity_t *ident) {
    if (!ident) {
        return NULL;
    }
    device_session_t *s = (device_session_t *)calloc(1, sizeof(*s));
    if (!s) {
        return NULL;
    }
    s->ident = *ident;
    s->rx = xQueueCreate(RX_QUEUE_LEN, sizeof(rx_msg_t *));
    if (!s->rx) {
        free(s);
        return NULL;
    }
    return s;
}

void device_session_destroy(device_session_t *s) {
    if (!s) {
        return;
    }
    if (s->command_task) {
        vTaskDelete(s->command_task);
        s->command_task = NULL;
    }
    if (s->events) {
        ws_transport_destroy(s->events);
        s->events = NULL;
    }
    if (s->tx) {
        ws_transport_destroy(s->tx);
    }
    if (s->rx) {
        rx_msg_t *m;
        while (xQueueReceive(s->rx, &m, 0) == pdTRUE) {
            rx_free(m);
        }
        vQueueDelete(s->rx);
    }
    free(s);
}

esp_err_t device_session_hello_json(const device_session_t *s, char *out, size_t cap) {
    if (!s || !out) {
        return ESP_ERR_INVALID_ARG;
    }
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "device_id", s->ident.device_id);
    cJSON_AddStringToObject(root, "boot_id", s->ident.boot_id);
    cJSON *caps = cJSON_AddArrayToObject(root, "capabilities");
    cJSON_AddItemToArray(caps, cJSON_CreateString("orient"));
    cJSON_AddItemToArray(caps, cJSON_CreateString("light"));
    cJSON_AddItemToArray(caps, cJSON_CreateString("speak"));
    cJSON_AddItemToArray(caps, cJSON_CreateString("stop"));
    cJSON *limits = cJSON_AddObjectToObject(root, "limits");
    cJSON_AddNumberToObject(limits, "yaw_min_deg", s->ident.yaw_min_deg);
    cJSON_AddNumberToObject(limits, "yaw_max_deg", s->ident.yaw_max_deg);
    char *txt = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (!txt) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t rc = (strlen(txt) < cap) ? ESP_OK : ESP_ERR_INVALID_SIZE;
    if (rc == ESP_OK) {
        strncpy(out, txt, cap - 1);
        out[cap - 1] = '\0';
    }
    cJSON_free(txt);
    return rc;
}

/* Connect a transport for `path` and wait for WS_EVT_CONNECTED. */
static esp_err_t open_ws(device_session_t *s, const char *path) {
    char uri[192];
    esp_err_t rc = ws_build_uri(s->ident.ws_scheme, s->ident.controller_url, path, uri, sizeof(uri));
    if (rc != ESP_OK) {
        return rc;
    }
    s->tx = ws_transport_create(uri, s->ident.media_token, on_ws, s);
    if (!s->tx) {
        return ESP_ERR_NO_MEM;
    }
    if (ws_transport_start(s->tx) != ESP_OK) {
        return ESP_FAIL;
    }
    rx_msg_t *m = NULL;
    if (xQueueReceive(s->rx, &m, pdMS_TO_TICKS(RX_TIMEOUT_MS)) != pdTRUE || !m) {
        return ESP_ERR_TIMEOUT;
    }
    ws_evt_type_t type = m->type;
    rx_free(m);
    return (type == WS_EVT_CONNECTED) ? ESP_OK : ESP_FAIL;
}

static void close_ws(device_session_t *s) {
    if (s->tx) {
        ws_transport_stop(s->tx);
        ws_transport_destroy(s->tx);
        s->tx = NULL;
    }
    rx_msg_t *m;
    while (xQueueReceive(s->rx, &m, 0) == pdTRUE) {
        rx_free(m);
    }
}

/* Pop the next message, waiting up to RX_TIMEOUT_MS. Caller frees via rx_free. */
static rx_msg_t *recv_msg(device_session_t *s) {
    rx_msg_t *m = NULL;
    if (xQueueReceive(s->rx, &m, pdMS_TO_TICKS(RX_TIMEOUT_MS)) != pdTRUE) {
        return NULL;
    }
    return m;
}

esp_err_t device_session_run_uplink(device_session_t *s, const char *session_id,
                                    const char *stream_id, uint32_t stream_key,
                                    const char *end_reason) {
    if (!s || !session_id || !stream_id || !end_reason) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t rc = open_ws(s, EFFMEET_WS_UPLINK_PATH);
    if (rc != ESP_OK) {
        ESP_LOGE(TAG, "uplink connect failed: %s", esp_err_to_name(rc));
        close_ws(s);
        return rc;
    }

    /* AudioStreamConfig (uplink / onsite_voice; command_id must be null). */
    cJSON *cfg = cJSON_CreateObject();
    cJSON_AddStringToObject(cfg, "schema_version", "1.0");
    cJSON_AddStringToObject(cfg, "type", "audio.start");
    cJSON_AddStringToObject(cfg, "session_id", session_id);
    cJSON_AddStringToObject(cfg, "meeting_id", s->ident.meeting_id);
    cJSON_AddStringToObject(cfg, "device_id", s->ident.device_id);
    cJSON_AddStringToObject(cfg, "stream_id", stream_id);
    cJSON_AddNumberToObject(cfg, "stream_key", stream_key);
    cJSON_AddStringToObject(cfg, "direction", "uplink");
    cJSON_AddStringToObject(cfg, "purpose", "onsite_voice");
    cJSON_AddNullToObject(cfg, "command_id");
    cJSON_AddNumberToObject(cfg, "sample_rate_hz", EFMA_SAMPLE_RATE_HZ);
    cJSON_AddNumberToObject(cfg, "channels", EFMA_CHANNELS);
    cJSON_AddStringToObject(cfg, "encoding", "s16le");
    cJSON_AddNumberToObject(cfg, "frame_ms", EFMA_FRAME_MS);
    char *cfg_txt = cJSON_PrintUnformatted(cfg);
    cJSON_Delete(cfg);
    rc = ws_transport_send_text(s->tx, cfg_txt);
    cJSON_free(cfg_txt);
    if (rc != ESP_OK) {
        close_ws(s);
        return rc;
    }

    /* Expect audio.ready. */
    rx_msg_t *m = recv_msg(s);
    if (!m || m->type != WS_EVT_TEXT) {
        rx_free(m);
        close_ws(s);
        return ESP_ERR_TIMEOUT;
    }
    cJSON *ready = cJSON_Parse((const char *)m->buf);
    rx_free(m);
    bool ok = ready && cJSON_HasObjectItem(ready, "accepted");
    if (ready) {
        cJSON_Delete(ready);
    }
    if (!ok) {
        close_ws(s);
        return ESP_FAIL;
    }

    /* Stream mic frames. audio_capture_read_frame() is a NOT-VERIFIED stub that
     * returns ESP_ERR_NOT_SUPPORTED until the I2S/AFE path is brought up, so this
     * loop currently exits immediately without sending audio. */
    uint8_t pcm[EFMA_BYTES_PER_FRAME];
    uint8_t frame[EFMA_HEADER_SIZE + EFMA_BYTES_PER_FRAME];
    size_t frame_len = 0;
    uint32_t seq = 0, start = 0;
    while (audio_capture_read_frame(pcm, sizeof(pcm)) == ESP_OK) {
        if (efma_encode_frame(stream_key, seq, start, pcm, sizeof(pcm),
                              frame, sizeof(frame), &frame_len) != EFMA_OK) {
            break;
        }
        if (ws_transport_send_bin(s->tx, frame, frame_len) != ESP_OK) {
            break;
        }
        /* Consume the per-frame audio.ack (media.py sends one per frame). */
        rx_msg_t *ack = recv_msg(s);
        rx_free(ack);
        seq += 1;
        start += EFMA_SAMPLES_PER_FRAME;
    }

    /* AudioStreamEnd. */
    cJSON *end = cJSON_CreateObject();
    cJSON_AddStringToObject(end, "type", "audio.end");
    cJSON_AddStringToObject(end, "session_id", session_id);
    cJSON_AddNumberToObject(end, "stream_key", stream_key);
    cJSON_AddStringToObject(end, "reason", end_reason);
    cJSON_AddNullToObject(end, "command_id");
    char *end_txt = cJSON_PrintUnformatted(end);
    cJSON_Delete(end);
    ws_transport_send_text(s->tx, end_txt);
    cJSON_free(end_txt);

    /* Drain audio.closed / utterance.final, then tear down. */
    rx_msg_t *tail;
    while ((tail = recv_msg(s)) != NULL) {
        rx_free(tail);
    }
    close_ws(s);
    return ESP_OK;
}

esp_err_t device_session_send_receipt(device_session_t *s, const char *command_id,
                                      receipt_status_t status, const char *error_code) {
    if (!s || !s->tx || !command_id) {
        return ESP_ERR_INVALID_ARG;
    }
    static const char *names[] = {"accepted", "started", "completed", "failed", "rejected"};
    cJSON *r = cJSON_CreateObject();
    cJSON_AddStringToObject(r, "command_id", command_id);
    cJSON_AddStringToObject(r, "target_device_id", s->ident.device_id);
    cJSON_AddStringToObject(r, "boot_id", s->ident.boot_id);
    cJSON_AddStringToObject(r, "status", names[status]);
    if (error_code) {
        cJSON_AddStringToObject(r, "error_code", error_code);
    } else {
        cJSON_AddNullToObject(r, "error_code");
    }
    char *txt = cJSON_PrintUnformatted(r);
    cJSON_Delete(r);
    if (!txt) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t rc = ws_transport_send_text(s->tx, txt);
    cJSON_free(txt);
    return rc;
}

esp_err_t device_session_run_playback(device_session_t *s, const char *command_id,
                                      bool safe_pause, const char *sink_mode) {
    if (!s || !command_id) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t rc = open_ws(s, EFFMEET_WS_PLAYBACK_PATH);
    if (rc != ESP_OK) {
        close_ws(s);
        return rc;
    }
    strncpy(s->playback_cmd, command_id, sizeof(s->playback_cmd) - 1);

    /* hello: {command_id, device_id, boot_id, safe_pause, sink_mode}.
     * safe_pause=true asserts a quiet moment; media.py rejects otherwise. This is
     * NOT calibrated VAD/AEC — see aec_afe.c for the real front-end hook. */
    cJSON *hello = cJSON_CreateObject();
    cJSON_AddStringToObject(hello, "command_id", command_id);
    cJSON_AddStringToObject(hello, "device_id", s->ident.device_id);
    cJSON_AddStringToObject(hello, "boot_id", s->ident.boot_id);
    cJSON_AddBoolToObject(hello, "safe_pause", safe_pause);
    cJSON_AddStringToObject(hello, "sink_mode", sink_mode ? sink_mode : "manual");
    char *hello_txt = cJSON_PrintUnformatted(hello);
    cJSON_Delete(hello);
    ws_transport_send_text(s->tx, hello_txt);
    cJSON_free(hello_txt);

    /* Expect audio.start (downlink AudioStreamConfig). */
    rx_msg_t *m = recv_msg(s);
    if (!m || m->type != WS_EVT_TEXT) {
        rx_free(m);
        device_session_send_receipt(s, command_id, RECEIPT_FAILED, "NO_AUDIO_START");
        close_ws(s);
        return ESP_FAIL;
    }
    cJSON *start = cJSON_Parse((const char *)m->buf);
    rx_free(m);
    cJSON *sid = start ? cJSON_GetObjectItem(start, "session_id") : NULL;
    cJSON *skey = start ? cJSON_GetObjectItem(start, "stream_key") : NULL;
    if (!sid || !skey) {
        if (start) cJSON_Delete(start);
        device_session_send_receipt(s, command_id, RECEIPT_FAILED, "BAD_AUDIO_START");
        close_ws(s);
        return ESP_FAIL;
    }
    char session_id[37];
    strncpy(session_id, sid->valuestring, sizeof(session_id) - 1);
    session_id[sizeof(session_id) - 1] = '\0';
    uint32_t stream_key = (uint32_t)skey->valuedouble;
    cJSON_Delete(start);

    /* AudioStreamReady (accepted). */
    cJSON *ready = cJSON_CreateObject();
    cJSON_AddStringToObject(ready, "type", "audio.ready");
    cJSON_AddStringToObject(ready, "session_id", session_id);
    cJSON_AddNumberToObject(ready, "stream_key", stream_key);
    cJSON_AddBoolToObject(ready, "accepted", true);
    cJSON_AddNullToObject(ready, "error_code");
    char *ready_txt = cJSON_PrintUnformatted(ready);
    cJSON_Delete(ready);
    ws_transport_send_text(s->tx, ready_txt);
    cJSON_free(ready_txt);

    /* Receipts: accepted then started (media.py receive_receipt order). */
    device_session_send_receipt(s, command_id, RECEIPT_ACCEPTED, NULL);
    device_session_send_receipt(s, command_id, RECEIPT_STARTED, NULL);
    status_led_set_pattern(LED_PATTERN_NOTICE);
    audio_playback_begin();

    /* Receive EFMA frames, decode, play, ack each. One outstanding frame max. */
    efma_decoder_t dec;
    efma_decoder_init(&dec, stream_key);
    uint8_t pcm[EFMA_MAX_DECODED];
    size_t pcm_len = 0;
    bool dup = false, gap = false;
    for (;;) {
        m = recv_msg(s);
        if (!m) {
            device_session_send_receipt(s, command_id, RECEIPT_FAILED, "PLAYBACK_TIMEOUT");
            break;
        }
        if (m->type == WS_EVT_BINARY) {
            if (efma_decode_frame(&dec, m->buf, m->len, pcm, sizeof(pcm),
                                  &pcm_len, &dup, &gap) == EFMA_OK && !dup) {
                audio_playback_write(pcm, pcm_len); /* NOT-VERIFIED stub */
                cJSON *ack = cJSON_CreateObject();
                cJSON_AddStringToObject(ack, "type", "audio.ack");
                cJSON_AddNumberToObject(ack, "sample_end", dec.samples);
                char *ack_txt = cJSON_PrintUnformatted(ack);
                cJSON_Delete(ack);
                ws_transport_send_text(s->tx, ack_txt);
                cJSON_free(ack_txt);
            }
            rx_free(m);
            continue;
        }
        if (m->type == WS_EVT_TEXT) {
            cJSON *msg = cJSON_Parse((const char *)m->buf);
            rx_free(m);
            cJSON *type = msg ? cJSON_GetObjectItem(msg, "type") : NULL;
            const char *t = (type && cJSON_IsString(type)) ? type->valuestring : "";
            if (strcmp(t, "audio.end") == 0) {
                if (msg) cJSON_Delete(msg);
                break;
            }
            if (strcmp(t, "error") == 0) {
                if (msg) cJSON_Delete(msg);
                device_session_send_receipt(s, command_id, RECEIPT_FAILED, "SERVER_ERROR");
                goto done;
            }
            if (msg) cJSON_Delete(msg);
        }
    }

    /* Drain until playback.closed, then attest completion. */
    audio_playback_end();
    device_session_send_receipt(s, command_id, RECEIPT_COMPLETED, NULL);
    status_led_set_pattern(LED_PATTERN_IDLE);
    {
        rx_msg_t *tail;
        while ((tail = recv_msg(s)) != NULL) {
            rx_free(tail);
        }
    }
done:
    close_ws(s);
    return ESP_OK;
}

esp_err_t device_session_on_command(device_session_t *s, const char *command_json) {
    if (!s || !command_json) {
        return ESP_ERR_INVALID_ARG;
    }
    cJSON *root = cJSON_Parse(command_json);
    if (!root) {
        return ESP_ERR_INVALID_ARG;
    }
    cJSON *action = cJSON_GetObjectItem(root, "action");
    cJSON *args = cJSON_GetObjectItem(root, "args");
    cJSON *cid = cJSON_GetObjectItem(root, "command_id");
    if (!cJSON_IsString(action)) {
        cJSON_Delete(root);
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t rc = ESP_OK;
    if (strcmp(action->valuestring, "orient") == 0) {
        cJSON *yaw = args ? cJSON_GetObjectItem(args, "yaw_deg") : NULL;
        cJSON *dur = args ? cJSON_GetObjectItem(args, "duration_ms") : NULL;
        if (cJSON_IsNumber(yaw) && cJSON_IsNumber(dur)) {
            rc = servo_yaw_move_to((float)yaw->valuedouble, (int)dur->valuedouble);
        }
    } else if (strcmp(action->valuestring, "light") == 0) {
        cJSON *pat = args ? cJSON_GetObjectItem(args, "pattern") : NULL;
        if (cJSON_IsString(pat)) {
            rc = status_led_set_pattern_name(pat->valuestring);
        }
    } else if (strcmp(action->valuestring, "stop") == 0) {
        audio_playback_stop();
        servo_yaw_stop();
        status_led_set_pattern(LED_PATTERN_IDLE);
    } else if (strcmp(action->valuestring, "speak") == 0) {
        /* speak is delivered by opening the playback WS for this command_id.
         * safe_pause must reflect a real quiet-moment attestation (aec_afe). */
        if (cJSON_IsString(cid)) {
            bool quiet = aec_afe_quiet_moment();
            rc = device_session_run_playback(s, cid->valuestring, quiet, "manual");
        }
    } else {
        rc = ESP_ERR_NOT_SUPPORTED;
    }
    cJSON_Delete(root);
    return rc;
}


/* ---- command subscription over the controller events WS ---- */

static void events_send_hello(device_session_t *s) {
    if (!s || !s->events) {
        return;
    }
    cJSON *hello = cJSON_CreateObject();
    cJSON_AddStringToObject(hello, "device_id", s->ident.device_id);
    cJSON_AddStringToObject(hello, "token", s->ident.media_token);
    cJSON_AddNumberToObject(hello, "after_seq", (double)s->after_seq);
    char *txt = cJSON_PrintUnformatted(hello);
    cJSON_Delete(hello);
    if (txt) {
        ws_transport_send_text(s->events, txt);
        cJSON_free(txt);
    }
}

static void on_events_ws(void *ctx, const ws_event_t *evt) {
    device_session_t *s = (device_session_t *)ctx;
    if (!s || !evt) {
        return;
    }
    if (evt->type == WS_EVT_CONNECTED) {
        events_send_hello(s);
        return;
    }
    if (evt->type != WS_EVT_TEXT || !evt->text) {
        return;
    }
    cJSON *root = cJSON_Parse(evt->text);
    if (!root) {
        return;
    }
    cJSON *seq = cJSON_GetObjectItem(root, "seq");
    if (cJSON_IsNumber(seq) && seq->valuedouble > 0) {
        s->after_seq = (uint32_t)seq->valuedouble;
    }
    cJSON *type = cJSON_GetObjectItem(root, "event_type");
    cJSON *payload = cJSON_GetObjectItem(root, "payload");
    if (cJSON_IsString(type) && cJSON_IsObject(payload)
            && strcmp(type->valuestring, "robot.command") == 0) {
        cJSON *target = cJSON_GetObjectItem(payload, "target_device_id");
        if (cJSON_IsString(target)
                && strcmp(target->valuestring, s->ident.device_id) == 0) {
            char *cmd = cJSON_PrintUnformatted(payload);
            if (cmd) {
                device_session_on_command(s, cmd);
                cJSON_free(cmd);
            }
        }
    }
    cJSON_Delete(root);
}

static void command_task(void *arg) {
    device_session_t *s = (device_session_t *)arg;
    char uri[512];
    char path[96];
    for (;;) {
        snprintf(path, sizeof(path), "/api/v1/meetings/%s/events", s->ident.meeting_id);
        if (ws_build_uri(s->ident.ws_scheme, s->ident.controller_url, path, uri,
                         sizeof(uri)) != ESP_OK) {
            vTaskDelay(pdMS_TO_TICKS(2000));
            continue;
        }
        s->events = ws_transport_create(uri, NULL, on_events_ws, s);
        if (s->events) {
            if (ws_transport_start(s->events) == ESP_OK) {
                while (ws_transport_is_connected(s->events)) {
                    vTaskDelay(pdMS_TO_TICKS(500));
                }
            }
            ws_transport_destroy(s->events);
            s->events = NULL;
        }
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

esp_err_t device_session_subscribe_commands(device_session_t *s) {
    if (!s) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!s->ident.meeting_id[0] || !s->ident.media_token[0]) {
        return ESP_ERR_INVALID_STATE;
    }
    if (xTaskCreate(command_task, "cmd", 4096, s, 4, &s->command_task) != pdTRUE) {
        return ESP_FAIL;
    }
    return ESP_OK;
}
