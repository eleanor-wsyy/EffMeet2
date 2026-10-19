"""Publish a WAV to a local LiveKit room as remote_1 and wait for real ASR ingest.

Prerequisites (all local, no cloud key, no device):
  livekit-server --dev ...            # ws://127.0.0.1:7880
  .venv-asr python scripts/run_local_asr.py
  run_bench.py --port 8772 with FUNASR_WS_URL + LIVEKIT_* env

The relay must be connected before the track is published. This script proves
remote audio -> LiveKit -> relay -> real FunASR -> utterance.final.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import wave
from pathlib import Path

import httpx
from livekit import rtc


def _wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                wav.getcomptype()) != (1, 2, 16000, "NONE"):
            raise ValueError("WAV must be 16 kHz mono 16-bit PCM")
        return wav.readframes(wav.getnframes())


async def _publish(url: str, token: str, pcm: bytes) -> None:
    room = rtc.Room()
    await room.connect(url, token)
    source = rtc.AudioSource(16000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("smoke-remote", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await room.local_participant.publish_track(track, options)
    for offset in range(0, len(pcm), 640):
        chunk = pcm[offset:offset + 640]
        await source.capture_frame(rtc.AudioFrame(chunk, 16000, 1, len(chunk) // 2))
        await asyncio.sleep(0.02)
    await asyncio.sleep(2)
    await room.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8772")
    parser.add_argument("--wav", default=str(Path(__file__).resolve().parents[1] / "data/acceptance_speech.wav"))
    parser.add_argument("--timeout", type=int, default=40)
    args = parser.parse_args()
    host = httpx.URL(args.base_url).host
    if host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("only localhost controller is allowed")
    wav = Path(args.wav)
    pcm = _wav_pcm(wav)
    with httpx.Client(base_url=args.base_url, timeout=15, trust_env=False) as http:
        session = http.get("/api/demo/session").json()
        tokens = {p["actor"]: p["token"] for p in session["profiles"]}
        headers = {"Authorization": "Bearer " + tokens["operator"]}
        meeting = http.post("/api/v1/meetings", json={"title": "remote audio smoke"},
                            headers=headers).json()["meeting_id"]
        remote_headers = {"Authorization": "Bearer " + tokens["remote_1"]}
        credentials = http.post(f"/api/v1/meetings/{meeting}/livekit-token",
                                json={"identity": "remote_1"}, headers=remote_headers).json()
        deadline = time.time() + args.timeout
        relay = None
        while time.time() < deadline:
            relay = http.get(f"/api/v1/meetings/{meeting}/livekit-status",
                             headers=headers).json()
            if relay.get("relay_connected"):
                break
            time.sleep(0.5)
        if not relay or not relay.get("relay_connected"):
            print(json.dumps({"status": "FAIL", "meeting_id": meeting,
                              "reason": "relay did not connect", "relay": relay}, ensure_ascii=False))
            return 1
        asyncio.run(_publish(credentials["url"], credentials["token"], pcm))
        seen = []
        while time.time() < deadline:
            state = http.get(f"/api/demo/meetings/{meeting}/state", headers=remote_headers).json()
            seen = [u for u in state.get("utterances", [])
                    if u.get("channel") == "remote" and u.get("speaker_id") == "remote_1"]
            if seen:
                break
            time.sleep(0.5)
    if not seen:
        print(json.dumps({"status": "FAIL", "meeting_id": meeting,
                          "reason": "no remote utterance before timeout"}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "meeting_id": meeting,
                      "utterances": seen, "wav": str(wav)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
