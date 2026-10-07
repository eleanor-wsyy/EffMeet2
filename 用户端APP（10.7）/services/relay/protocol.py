"""EFMA v1 framing. PCM is little endian; the wire header is big endian."""
import struct

HEADER = struct.Struct("!4sBBHIIII")


class ProtocolError(ValueError):
    pass


def encode_frame(key, seq, start, pcm):
    if not pcm or len(pcm) % 2 or len(pcm) > 640:
        raise ProtocolError("INVALID_PAYLOAD")
    return HEADER.pack(b"EFMA", 1, 0, 24, key, seq, start, len(pcm) // 2) + pcm


class Decoder:
    def __init__(self, key):
        self.key, self.seq, self.samples = key, 0, 0

    def feed(self, frame):
        if len(frame) < HEADER.size:
            raise ProtocolError("SHORT_HEADER")
        magic, version, flags, size, key, seq, start, count = HEADER.unpack_from(frame)
        if (magic, version, flags, size) != (b"EFMA", 1, 0, 24):
            raise ProtocolError("INVALID_HEADER")
        if key != self.key:
            raise ProtocolError("WRONG_STREAM")
        if not 1 <= count <= 320 or len(frame) != 24 + count * 2:
            raise ProtocolError("INVALID_PAYLOAD")
        if seq < self.seq:
            return b"", "duplicate"
        gap = start - self.samples
        if gap < 0 or (seq == self.seq and gap != 0) or (seq > self.seq and gap <= 0):
            raise ProtocolError("INVALID_SEQUENCE")
        # Bounded concealment: large discontinuities require a fresh session.
        if gap > 3200 or seq - self.seq > 10:
            raise ProtocolError("GAP_TOO_LARGE")
        if start + count > 0xFFFFFFFF or seq == 0xFFFFFFFF:
            raise ProtocolError("SESSION_WRAP")
        self.seq, self.samples = seq + 1, start + count
        return bytes(gap * 2) + frame[24:], "gap" if gap else "ok"
