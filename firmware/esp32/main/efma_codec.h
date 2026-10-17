/* EFMA v1 frame codec — faithful C port of services/relay/protocol.py.
 *
 * Wire header is 24 bytes, big-endian, struct "!4sBBHIIII":
 *   [0..3]   magic   "EFMA"
 *   [4]      version  u8  = 1
 *   [5]      flags    u8  = 0
 *   [6..7]   size     u16 = 24
 *   [8..11]  key      u32 (stream_key)
 *   [12..15] seq      u32 (frame sequence, starts at 0)
 *   [16..19] start    u32 (sample offset of first payload sample)
 *   [20..23] count    u32 (payload samples; 1..320)
 *   [24..]   payload  count * 2 bytes, 16 kHz mono s16le
 *
 * Pure C (no ESP-IDF headers) so it can be unit-tested on the host; see
 * ../test/test_efma_host.c. NOT-VERIFIED against a real device link.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EFMA_MAGIC          "EFMA"
#define EFMA_VERSION        1
#define EFMA_FLAGS          0
#define EFMA_HEADER_SIZE    24
#define EFMA_MAX_PAYLOAD    640   /* 320 samples * 2 bytes (20 ms @ 16 kHz) */
#define EFMA_MAX_SAMPLES    320
#define EFMA_MAX_GAP_SAMPLES 3200 /* beyond this the session must be reset */
#define EFMA_MAX_SEQ_JUMP   10
/* Largest decoded output: gap concealment zeros + one full payload. */
#define EFMA_MAX_DECODED    (EFMA_MAX_GAP_SAMPLES * 2 + EFMA_MAX_PAYLOAD)

typedef enum {
    EFMA_OK = 0,
    EFMA_ERR_SHORT_HEADER = -1,
    EFMA_ERR_INVALID_HEADER = -2,
    EFMA_ERR_WRONG_STREAM = -3,
    EFMA_ERR_INVALID_PAYLOAD = -4,
    EFMA_ERR_INVALID_SEQUENCE = -5,
    EFMA_ERR_GAP_TOO_LARGE = -6,
    EFMA_ERR_SESSION_WRAP = -7,
    EFMA_ERR_BAD_ARG = -8,
} efma_err_t;

/* Encode one frame. pcm_len must be even, 1..EFMA_MAX_PAYLOAD.
 * out must have room for EFMA_HEADER_SIZE + pcm_len bytes.
 * Returns EFMA_OK and sets *out_len, or a negative efma_err_t. */
efma_err_t efma_encode_frame(uint32_t key, uint32_t seq, uint32_t start,
                             const uint8_t *pcm, size_t pcm_len,
                             uint8_t *out, size_t out_cap, size_t *out_len);

typedef struct {
    uint32_t key;
    uint32_t seq;      /* next expected seq */
    uint32_t samples;  /* next expected sample offset */
} efma_decoder_t;

void efma_decoder_init(efma_decoder_t *d, uint32_t key);

/* Decode one frame, mirroring Decoder.feed(). On EFMA_OK:
 *   *duplicate = true  -> seq < expected; no new audio written (out_pcm_len 0)
 *   *gap       = true  -> concealment zeros were prepended before payload
 *   out_pcm/out_pcm_len -> written audio (<= EFMA_MAX_DECODED bytes)
 * Returns EFMA_OK or a negative efma_err_t (state unchanged on error). */
efma_err_t efma_decode_frame(efma_decoder_t *d, const uint8_t *frame, size_t frame_len,
                             uint8_t *out_pcm, size_t out_cap, size_t *out_pcm_len,
                             bool *duplicate, bool *gap);

#ifdef __cplusplus
}
#endif
