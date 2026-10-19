/* Host-side unit test for the EFMA codec. Pure C, no ESP-IDF.
 *
 * Build & run on a dev machine with a C compiler:
 *   gcc -std=c11 -Wall -Wextra -I../main test_efma_host.c ../main/efma_codec.c -o test_efma
 *   ./test_efma
 * Or from the repo root (no system compiler required):
 *   python -m pip install ziglang
 *   python scripts/test_efma_host.py
 *
 * Assertions mirror services/relay/protocol.py behaviour. Passed on the host
 * with ziglang on 2026-10-19; NOT verified on a device link.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "efma_codec.h"

static void fill(uint8_t *buf, size_t n, uint8_t seed) {
    for (size_t i = 0; i < n; i++) {
        buf[i] = (uint8_t)(seed + i);
    }
}

int main(void) {
    uint8_t pcm[EFMA_MAX_PAYLOAD];
    uint8_t frame[EFMA_HEADER_SIZE + EFMA_MAX_PAYLOAD];
    uint8_t out[EFMA_MAX_DECODED];
    size_t frame_len = 0, out_len = 0;
    bool dup = false, gap = false;
    fill(pcm, sizeof(pcm), 1);

    /* Encode a full 640-byte (320-sample) frame. */
    assert(efma_encode_frame(7, 0, 0, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(frame_len == 24 + 640);
    assert(memcmp(frame, "EFMA", 4) == 0);
    assert(frame[4] == 1 && frame[5] == 0);

    /* Reject odd / oversized / empty payloads like protocol.py. */
    assert(efma_encode_frame(7, 0, 0, pcm, 641, frame, sizeof(frame), &frame_len) == EFMA_ERR_INVALID_PAYLOAD);
    assert(efma_encode_frame(7, 0, 0, pcm, 0, frame, sizeof(frame), &frame_len) == EFMA_ERR_INVALID_PAYLOAD);

    /* Decode contiguous frames: seq 0 then seq 1. */
    efma_decoder_t d;
    efma_decoder_init(&d, 7);
    assert(efma_encode_frame(7, 0, 0, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    assert(out_len == 640 && !dup && !gap);
    assert(d.seq == 1 && d.samples == 320);

    assert(efma_encode_frame(7, 1, 320, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    assert(out_len == 640 && !dup && !gap);
    assert(d.seq == 2 && d.samples == 640);

    /* Duplicate (seq < expected) yields no audio, state unchanged. */
    assert(efma_encode_frame(7, 0, 0, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    assert(dup && out_len == 0 && d.seq == 2);

    /* Wrong stream key. */
    assert(efma_encode_frame(9, 2, 640, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_ERR_WRONG_STREAM);

    /* Small gap (<= 3200 samples) -> concealment zeros prepended. */
    efma_decoder_init(&d, 7);
    assert(efma_encode_frame(7, 0, 0, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    /* Jump ahead: seq 5, start 320 + 100 samples gap. */
    assert(efma_encode_frame(7, 5, 420, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    assert(gap && out_len == 100 * 2 + 640);

    /* Gap too large (> 3200 samples). */
    efma_decoder_init(&d, 7);
    assert(efma_encode_frame(7, 1, 5000, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_ERR_GAP_TOO_LARGE);

    /* Invalid sequence: start regresses. */
    efma_decoder_init(&d, 7);
    assert(efma_encode_frame(7, 0, 0, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_OK);
    assert(efma_encode_frame(7, 1, 100, pcm, 640, frame, sizeof(frame), &frame_len) == EFMA_OK);
    assert(efma_decode_frame(&d, frame, frame_len, out, sizeof(out), &out_len, &dup, &gap) == EFMA_ERR_INVALID_SEQUENCE);

    /* Short header. */
    assert(efma_decode_frame(&d, frame, 10, out, sizeof(out), &out_len, &dup, &gap) == EFMA_ERR_SHORT_HEADER);

    printf("EFMA host tests passed (protocol.py parity).\n");
    return 0;
}
