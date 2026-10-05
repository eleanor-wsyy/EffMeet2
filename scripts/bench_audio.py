"""Local WAV input or bounded PCM playback client. Credentials stay in memory."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from uuid import uuid4
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from websockets.asyncio.client import connect
from services.relay.protocol import Decoder, encode_frame


async def run(args):
    parsed = urlsplit(args.url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only localhost bench endpoints are supported")
    base = args.url.rstrip("/")
    async with httpx.AsyncClient(base_url=base, trust_env=False) as http:
        session = (await http.get("/api/demo/session")).json()
        if session["mode"] != "bench":
            raise ValueError("This command requires run_bench.py")
        headers = {"Authorization": "Bearer " + next(p["token"] for p in session["profiles"] if p["actor"] == "operator")}
        async def post(path, body=None):
            response = await http.post(path, json=body, headers=headers)
            response.raise_for_status()
            return response.json()
        device = "host_speaker_test" if args.command == "play" else "bench_mic"
        pair = await post(f"/api/v1/meetings/{args.meeting}/devices/{device}/pair")
        media_headers = {"Authorization": "Bearer " + pair["media_token"]}
        if args.command == "upload":
            with wave.open(args.wav, "rb") as wav:
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
                    raise ValueError("WAV must be 16kHz mono 16-bit PCM")
                if not 0 < wav.getnframes() <= 480000:
                    raise ValueError("WAV must contain 1..480000 samples (up to 30s)")
                pcm = wav.readframes(wav.getnframes())
            config = {"schema_version": "1.0", "type": "audio.start", "session_id": str(uuid4()),
                "meeting_id": args.meeting, "device_id": device, "stream_id": "bench_mic",
                "stream_key": 1, "direction": "uplink", "purpose": "onsite_voice", "command_id": None,
                "sample_rate_hz": 16000, "channels": 1, "encoding": "s16le", "frame_ms": 20}
            await post(f"/api/bench/meetings/{args.meeting}/media-bindings", {
                "config": config, "speaker_id": args.speaker, "channel": args.channel, "start_ms": args.start_ms})
            async with connect(base.replace("http://", "ws://", 1) + "/device/v1/audio", additional_headers=media_headers, proxy=None) as ws:
                await ws.send(json.dumps(config))
                ready = json.loads(await ws.recv())
                if not ready.get("accepted"):
                    raise RuntimeError(ready)
                for seq, offset in enumerate(range(0, len(pcm), 640)):
                    await ws.send(encode_frame(1, seq, offset // 2, pcm[offset:offset + 640]))
                    ack = json.loads(await ws.recv())
                    if ack.get("type") != "audio.ack":
                        raise RuntimeError(ack)
                await ws.send(json.dumps({"type": "audio.end", "session_id": config["session_id"],
                    "stream_key": 1, "reason": "completed", "command_id": None}))
                while True:
                    result = json.loads(await asyncio.wait_for(ws.recv(), 35))
                    print(json.dumps(result, ensure_ascii=False))
                    if result["type"] == "error":
                        raise RuntimeError(result["error_code"])
                    if result["type"] == "audio.closed":
                        break
        else:
            if not args.safe_pause:
                raise ValueError("Wait for a quiet moment, then pass --safe-pause")
            output = None
            if not args.simulate:
                import sounddevice as sd
                output = sd.RawOutputStream(samplerate=16000, channels=1, dtype="int16", blocksize=320, latency="low")
            cid, boot, decoder = args.command_id, str(uuid4()), Decoder(1)
            async with connect(base.replace("http://", "ws://", 1) + "/device/v1/playback", additional_headers=media_headers, proxy=None) as ws:
                await ws.send(json.dumps({"command_id": cid, "device_id": device, "boot_id": boot, "safe_pause": True,
                                          "sink_mode": "mock" if args.simulate else "manual"}))
                config = json.loads(await ws.recv())
                if config.get("type") != "audio.start":
                    raise RuntimeError(config)
                await ws.send(json.dumps({"type": "audio.ready", "session_id": config["session_id"],
                    "stream_key": 1, "accepted": True, "error_code": None}))
                async def receipt(status):
                    await ws.send(json.dumps({"command_id": cid, "target_device_id": device,
                        "boot_id": boot, "status": status, "error_code": None}))
                try:
                    await receipt("accepted")
                    if output:
                        output.start()
                    await receipt("started")
                    while True:
                        frame = await ws.recv()
                        if isinstance(frame, bytes):
                            pcm, _ = decoder.feed(frame)
                            if output:
                                underflow = await asyncio.to_thread(output.write, pcm)
                                if underflow:
                                    raise RuntimeError("PLAYBACK_UNDERFLOW")
                            else:
                                await asyncio.sleep(len(pcm) / 32000)
                            await ws.send(json.dumps({"type": "audio.ack", "sample_end": decoder.samples}))
                        else:
                            event = json.loads(frame)
                            if event.get("type") == "error":
                                raise RuntimeError(event["error_code"])
                            if event.get("type") == "audio.end":
                                if event["reason"] != "completed":
                                    raise RuntimeError(event["reason"])
                                if output:
                                    # PortAudio stop drains pending samples; abort below cancels on failure.
                                    await asyncio.to_thread(output.stop)
                                await receipt("completed")
                            elif event.get("type") == "playback.closed":
                                print(json.dumps({"status": "completed", "sink": "simulated" if args.simulate else "host_audio",
                                                  "samples": decoder.samples}))
                                break
                finally:
                    if output:
                        output.abort()
                        output.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    parser.add_argument("--meeting", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("upload")
    up.add_argument("wav")
    up.add_argument("--speaker", default=None)
    up.add_argument("--channel", choices=["onsite", "remote"], default="onsite")
    up.add_argument("--start-ms", type=int, default=0)
    play = sub.add_parser("play")
    play.add_argument("command_id")
    play.add_argument("--safe-pause", action="store_true")
    play.add_argument("--simulate", action="store_true", help="No audio output; simulated drain only")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
