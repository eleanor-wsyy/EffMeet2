/* EFMA v1 codec implementation. Mirrors services/relay/protocol.py field-by-field.
 * Pure C, no ESP-IDF dependency -> host-testable (../test/test_efma_host.c).
 * NOT-VERIFIED against a real device link.
 */
#include "efma_codec.h"

#include <string.h>

static void put_u16_be(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v >> 8);
    p[1] = (uint8_t)(v & 0xFF);
}

static void put_u32_be(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)(v & 0xFF);
}

static uint16_t get_u16_be(const uint8_t *p) {
    return (uint16_t)(((uint16_t)p[0] << 8) | (uint16_t)p[1]);
}

static uint32_t get_u32_be(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

efma_err_t efma_encode_frame(uint32_t key, uint32_t seq, uint32_t start,
                             const uint8_t *pcm, size_t pcm_len,
                             uint8_t *out, size_t out_cap, size_t *out_len) {
    if (!pcm || !out || !out_len) {
        return EFMA_ERR_BAD_ARG;
    }
    /* protocol.py: if not pcm or len(pcm) % 2 or len(pcm) > 640 -> INVALID_PAYLOAD */
    if (pcm_len == 0 || (pcm_len % 2) != 0 || pcm_len > EFMA_MAX_PAYLOAD) {
        return EFMA_ERR_INVALID_PAYLOAD;
    }
    if (out_cap < EFMA_HEADER_SIZE + pcm_len) {
        return EFMA_ERR_BAD_ARG;
    }
    memcpy(out, EFMA_MAGIC, 4);
    out[4] = EFMA_VERSION;
    out[5] = EFMA_FLAGS;
    put_u16_be(out + 6, EFMA_HEADER_SIZE);
    put_u32_be(out + 8, key);
    put_u32_be(out + 12, seq);
    put_u32_be(out + 16, start);
    put_u32_be(out + 20, (uint32_t)(pcm_len / 2)); /* count = samples */
    memcpy(out + EFMA_HEADER_SIZE, pcm, pcm_len);
    *out_len = EFMA_HEADER_SIZE + pcm_len;
    return EFMA_OK;
}

void efma_decoder_init(efma_decoder_t *d, uint32_t key) {
    if (!d) {
        return;
    }
    d->key = key;
    d->seq = 0;
    d->samples = 0;
}

efma_err_t efma_decode_frame(efma_decoder_t *d, const uint8_t *frame, size_t frame_len,
                             uint8_t *out_pcm, size_t out_cap, size_t *out_pcm_len,
                             bool *duplicate, bool *gap) {
    if (!d || !frame || !out_pcm || !out_pcm_len || !duplicate || !gap) {
        return EFMA_ERR_BAD_ARG;
    }
    *out_pcm_len = 0;
    *duplicate = false;
    *gap = false;

    if (frame_len < EFMA_HEADER_SIZE) {
        return EFMA_ERR_SHORT_HEADER;
    }
    if (memcmp(frame, EFMA_MAGIC, 4) != 0 || frame[4] != EFMA_VERSION ||
        frame[5] != EFMA_FLAGS || get_u16_be(frame + 6) != EFMA_HEADER_SIZE) {
        return EFMA_ERR_INVALID_HEADER;
    }
    uint32_t key = get_u32_be(frame + 8);
    uint32_t seq = get_u32_be(frame + 12);
    uint32_t start = get_u32_be(frame + 16);
    uint32_t count = get_u32_be(frame + 20);

    if (key != d->key) {
        return EFMA_ERR_WRONG_STREAM;
    }
    if (count < 1 || count > EFMA_MAX_SAMPLES ||
        frame_len != (size_t)EFMA_HEADER_SIZE + (size_t)count * 2) {
        return EFMA_ERR_INVALID_PAYLOAD;
    }
    /* seq < expected -> duplicate; no new audio, state unchanged. */
    if (seq < d->seq) {
        *duplicate = true;
        return EFMA_OK;
    }

    int64_t gap_samples = (int64_t)start - (int64_t)d->samples;
    if (gap_samples < 0 ||
        (seq == d->seq && gap_samples != 0) ||
        (seq > d->seq && gap_samples <= 0)) {
        return EFMA_ERR_INVALID_SEQUENCE;
    }
    if (gap_samples > EFMA_MAX_GAP_SAMPLES || (seq - d->seq) > EFMA_MAX_SEQ_JUMP) {
        return EFMA_ERR_GAP_TOO_LARGE;
    }
    if (((uint64_t)start + (uint64_t)count) > 0xFFFFFFFFULL || seq == 0xFFFFFFFFu) {
        return EFMA_ERR_SESSION_WRAP;
    }

    size_t conceal_bytes = (size_t)gap_samples * 2;
    size_t payload_bytes = (size_t)count * 2;
    size_t total = conceal_bytes + payload_bytes;
    if (out_cap < total) {
        return EFMA_ERR_BAD_ARG;
    }
    if (conceal_bytes) {
        memset(out_pcm, 0, conceal_bytes);
        *gap = true;
    }
    memcpy(out_pcm + conceal_bytes, frame + EFMA_HEADER_SIZE, payload_bytes);
    *out_pcm_len = total;

    d->seq = seq + 1;
    d->samples = start + count;
    return EFMA_OK;
}
