"""Bounded utterance-at-a-time FunASR WebSocket adapter (no raw retention)."""
import asyncio
import json
from urllib.parse import urlsplit

from websockets.asyncio.client import connect


class FunASR:
    mode = "real"

    def __init__(self, url, timeout=30):
        parsed = urlsplit(url)
        if parsed.scheme not in {"ws", "wss"} or parsed.username or parsed.password:
            raise ValueError("FUNASR_WS_URL must be a ws/wss service URL without credentials")
        if parsed.scheme == "ws" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Use wss for non-loopback FunASR")
        self.url, self.timeout = url, timeout

    async def transcribe(self, pcm, session_id):
        if not pcm or len(pcm) > 960000:
            raise ValueError("ASR requires 1..30 seconds of 16k mono PCM")
        async with asyncio.timeout(self.timeout):
            async with connect(self.url, proxy=None, max_size=65536, open_timeout=5) as ws:
                await ws.send(json.dumps({"mode": "offline", "wav_name": session_id,
                    "wav_format": "pcm", "audio_fs": 16000, "is_speaking": True, "itn": True}))
                for offset in range(0, len(pcm), 32000):
                    await ws.send(pcm[offset:offset + 32000])
                await ws.send(json.dumps({"is_speaking": False}))
                while True:
                    result = json.loads(await ws.recv())
                    # Offline servers may report is_final=false even for the sole final response.
                    if result.get("mode") != "offline":
                        continue
                    if result.get("wav_name") not in {None, session_id}:
                        raise ValueError("ASR_SESSION_MISMATCH")
                    text = result.get("text")
                    if not isinstance(text, str) or len(text) > 2000:
                        raise ValueError("INVALID_ASR_TEXT")
                    return text.strip()
