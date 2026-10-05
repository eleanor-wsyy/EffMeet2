"""Local bench media routes; shared controller store, no public listener."""
import asyncio
import json
import struct
import time
from uuid import uuid4, uuid5, NAMESPACE_URL

from fastapi import WebSocket, WebSocketDisconnect
from services.controller.contracts import DemoError, validate
from .protocol import Decoder, ProtocolError, encode_frame


def bearer(ws):
    value = ws.headers.get("authorization", "")
    return value[7:] if value.startswith("Bearer ") else ""


def local(ws):
    return (ws.client.host in {"127.0.0.1", "::1", "testclient"}
            and not ws.headers.get("origin") and not ws.query_params)


def install_media(app, bench, asr=None):
    @app.websocket("/device/v1/audio")
    async def uplink(ws: WebSocket):
        if not local(ws) or not bearer(ws):
            await ws.close(code=4403)
            return
        await ws.accept()
        sid, config, end_reason = None, None, "error"
        try:
            config = await asyncio.wait_for(ws.receive_json(), 5)
            validate("AudioStreamConfig", config)
            binding = bench.claim_binding(config, bearer(ws))
            sid = config["session_id"]
            if config["meeting_id"] in bench.speaking:
                raise ProtocolError("PLAYBACK_ACTIVE")
            opened = bench.store.open_audio_session(config["meeting_id"], config)
            await ws.send_json(opened["ready"])
            decoder, pcm = Decoder(config["stream_key"]), bytearray()
            async with asyncio.timeout(40):
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        raise WebSocketDisconnect()
                    if message.get("bytes") is not None:
                        if config["meeting_id"] in bench.speaking:
                            raise ProtocolError("PLAYBACK_ACTIVE")
                        audio, diagnostic = decoder.feed(message["bytes"])
                        if len(pcm) + len(audio) > 960000:
                            raise ProtocolError("SESSION_TOO_LONG")
                        pcm.extend(audio)
                        if audio and max(abs(x[0]) for x in struct.iter_unpack("<h", audio)) > 500:
                            bench.last_voice[config["meeting_id"]] = time.monotonic()
                        await ws.send_json({"type": "audio.ack", "session_id": sid,
                            "sample_end": decoder.samples, "diagnostic": diagnostic})
                    elif message.get("text"):
                        end = json.loads(message["text"])
                        validate("AudioStreamEnd", end)
                        if end["session_id"] != sid or end["stream_key"] != config["stream_key"] or end["command_id"] is not None:
                            raise ProtocolError("END_MISMATCH")
                        end_reason = end["reason"]
                        break
            if end_reason == "completed" and pcm:
                if asr is None:
                    raise ProtocolError("ASR_NOT_CONFIGURED")
                # Awaiting ASR never holds the event loop or a database transaction.
                text = await asr.transcribe(bytes(pcm), sid)
                if text:
                    utterance = {"utterance_id": str(uuid5(NAMESPACE_URL, "effmeet-asr:" + sid)),
                        "stream_id": config["stream_id"], "speaker_id": binding["speaker"],
                        "channel": binding["channel"], "start_ms": binding["start_ms"],
                        "end_ms": binding["start_ms"] + decoder.samples // 16,
                        "text": text, "final": True, "revision": 1}
                    result = bench.store.add_utterance(config["meeting_id"], utterance,
                        mode=asr.mode, source="funasr_offline", producer="asr")
                    await ws.send_json({"type": "utterance.final", "event": result["event"]})
            await ws.send_json({"type": "audio.closed", "session_id": sid, "reason": end_reason})
        except WebSocketDisconnect:
            pass
        except (DemoError, ProtocolError, ValueError, KeyError, TypeError, TimeoutError) as exc:
            end_reason = "error"
            code = exc.code if isinstance(exc, DemoError) else str(exc) if isinstance(exc, ProtocolError) else "INVALID_MEDIA_OR_TIMEOUT"
            await ws.send_json({"type": "error", "error_code": code})
        except Exception:
            end_reason = "error"
            await ws.send_json({"type": "error", "error_code": "ASR_UNAVAILABLE"})
        finally:
            if sid:
                bench.close_binding(sid)
                try:
                    bench.store.end_audio_session(config["meeting_id"], {"type": "audio.end", "session_id": sid,
                        "stream_key": config["stream_key"], "reason": end_reason, "command_id": None})
                except DemoError:
                    pass
            try:
                await ws.close()
            except RuntimeError:
                pass

    @app.websocket("/device/v1/playback")
    async def playback(ws: WebSocket):
        if not local(ws) or not bearer(ws):
            await ws.close(code=4403)
            return
        await ws.accept()
        cid, mid, claimed, sid, cancel = None, None, False, None, asyncio.Event()
        try:
            hello = await asyncio.wait_for(ws.receive_json(), 5)
            cid, device, boot = hello["command_id"], hello["device_id"], hello["boot_id"]
            # Synthesis precedes claim; no audio can be sent until a current confirmation is checked.
            row = bench.command(cid)
            bench.authenticate(device, bearer(ws), row["meeting_id"])
            command = json.loads(row["data"])
            if row["state"] != "queued" or command["target_device_id"] != device:
                raise ProtocolError("COMMAND_NOT_QUEUED")
            if bench.tts is None:
                raise ProtocolError("TTS_NOT_CONFIGURED")
            if cid in bench.active:
                raise ProtocolError("COMMAND_BUSY")
            bench.active[cid] = cancel
            pcm = await asyncio.wait_for(asyncio.to_thread(bench.tts.synthesize, command["args"]["text"]), 35)
            if cancel.is_set():
                raise ProtocolError("CANCELLED")
            if not pcm or len(pcm) % 2 or len(pcm) > 960000:
                raise ProtocolError("INVALID_TTS_AUDIO")
            # A bench player must explicitly attest a quiet moment. This is not calibrated VAD/AEC.
            if hello.get("safe_pause") is not True:
                raise ProtocolError("SAFE_PAUSE_REQUIRED")
            mid = row["meeting_id"]
            if mid in bench.speaking or time.monotonic() - bench.last_voice.get(mid, 0) < 1:
                raise ProtocolError("VOICE_ACTIVE")
            command, mid = bench.claim_command(cid, device, bearer(ws), boot, hello.get("sink_mode", "manual"))
            claimed = True
            bench.speaking.add(mid)
            sid = str(uuid4())
            cfg = {"schema_version": "1.0", "type": "audio.start", "session_id": sid,
                "meeting_id": mid, "device_id": device, "stream_id": "tts_robot", "stream_key": 1,
                "direction": "downlink", "purpose": "robot_tts", "command_id": cid,
                "sample_rate_hz": 16000, "channels": 1, "encoding": "s16le", "frame_ms": 20}
            await ws.send_json(cfg)
            ready = await asyncio.wait_for(ws.receive_json(), command["ttl_ms"] / 1000)
            validate("AudioStreamReady", ready)
            if not ready["accepted"] or ready["session_id"] != sid or ready["stream_key"] != 1:
                raise ProtocolError("READY_MISMATCH")

            async def receive_receipt(expected):
                r = await asyncio.wait_for(ws.receive_json(), 2)
                if r.get("command_id") != cid or r.get("boot_id") != boot or r.get("target_device_id") != device:
                    raise ProtocolError("RECEIPT_MISMATCH")
                if r.get("status") != expected:
                    raise ProtocolError("RECEIPT_ORDER")
                bench.receipt(r)

            await receive_receipt("accepted")
            await receive_receipt("started")
            if cancel.is_set():
                raise ProtocolError("CANCELLED")
            with bench.store.db() as conn:
                if bench.store.context_seq(conn, mid) != row["context_seq"]:
                    raise ProtocolError("STALE_COMMAND")
                dispatch = conn.execute("SELECT expires FROM bench_dispatch WHERE id=?", (cid,)).fetchone()
            if time.time() >= dispatch["expires"]:
                raise ProtocolError("COMMAND_EXPIRED")
            deadline = time.monotonic() + len(pcm) / 32000 + 10
            # One 20ms outstanding frame: bounded well below the 200ms playback queue limit.
            for seq, offset in enumerate(range(0, len(pcm), 640)):
                if cancel.is_set():
                    raise ProtocolError("CANCELLED")
                if time.monotonic() >= deadline:
                    raise ProtocolError("PLAYBACK_TIMEOUT")
                chunk = pcm[offset:offset + 640]
                await ws.send_bytes(encode_frame(1, seq, offset // 2, chunk))
                ack_task = asyncio.create_task(ws.receive_json())
                stop_task = asyncio.create_task(cancel.wait())
                try:
                    done, _ = await asyncio.wait({ack_task, stop_task}, timeout=2, return_when=asyncio.FIRST_COMPLETED)
                    if stop_task in done:
                        raise ProtocolError("CANCELLED")
                    if ack_task not in done:
                        raise ProtocolError("PLAYBACK_TIMEOUT")
                    ack = ack_task.result()
                    if ack.get("type") != "audio.ack" or ack.get("sample_end") != (offset + len(chunk)) // 2:
                        raise ProtocolError("ACK_MISMATCH")
                finally:
                    for task in (ack_task, stop_task):
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(ack_task, stop_task, return_exceptions=True)
            if cancel.is_set():
                raise ProtocolError("CANCELLED")
            await ws.send_json({"type": "audio.end", "session_id": sid, "stream_key": 1,
                "reason": "completed", "command_id": cid})
            await receive_receipt("completed")
            await ws.send_json({"type": "playback.closed", "command_id": cid})
        except Exception as exc:
            code = str(exc) if isinstance(exc, ProtocolError) else exc.code if isinstance(exc, DemoError) else "PLAYBACK_FAILED"
            if claimed:
                bench.fail_command(cid, code)
            try:
                if sid:
                    await ws.send_json({"type": "audio.end", "session_id": sid, "stream_key": 1,
                        "reason": "stopped" if code == "CANCELLED" else "error", "command_id": cid})
                await ws.send_json({"type": "error", "error_code": code})
            except (RuntimeError, WebSocketDisconnect):
                pass
        finally:
            if cid and bench.active.get(cid) is cancel:
                bench.active.pop(cid, None)
            if claimed:
                bench.speaking.discard(mid)
            try:
                await ws.close()
            except RuntimeError:
                pass
