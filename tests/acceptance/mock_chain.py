"""Mock-mode chain driver for the acceptance harness.

Drives the REAL controller + relay software (services/controller/app.py, bench,
media WS) with synthetic ASR/TTS/model, mirroring the accepted bench flow in
tests/test_bench.py, but at acceptance granularity: it returns per-stage evidence
for S1..S6 so the harness can prove its wiring end to end.

This is NOT real acceptance. Every stage here runs on fakes/loopback; the result
status is MOCK_OK (see harness.py). It is runnable in CI without hardware.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from services.controller.app import create_app
from services.controller.fakes import FakeAnalyzer
from services.relay.protocol import encode_frame


class _StubASR:
    mode = "mock"

    def __init__(self):
        self.pcm = b""

    async def transcribe(self, pcm, sid):
        self.pcm = pcm
        return "建议先验证草图再开模。"


class _StubTTS:
    def synthesize(self, text):
        return bytes(1280)  # two 640-byte EFMA frames


class _StubModel:
    mode = "real"  # exercise the external-adapter path; output is explicitly mock

    def analyze(self, evidence, status):
        return FakeAnalyzer().analyze(evidence, "possibly_unresponded")


def _drain_loop() -> None:
    """Best-effort asyncio cleanup so TestClient teardown is quiet on 3.13+."""
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        if not loop.is_closed():
            loop.close()
    except RuntimeError:
        pass


def run_mock_chain() -> dict[str, dict]:
    """Execute S1..S6 against the real software stack; return per-stage evidence."""
    ev: dict[str, dict] = {}
    tmp = TemporaryDirectory()
    asr = _StubASR()
    app = create_app(Path(tmp.name) / "acc.db", bench=True, asr=asr,
                     tts=_StubTTS(), analyzer=_StubModel())
    client = TestClient(app)
    client.__enter__()
    try:
        runtime = app.state.bench
        tokens = {p["actor"]: p["token"]
                  for p in client.get("/api/demo/session").json()["profiles"]}

        def post(path, body=None, expected=200, actor="operator"):
            r = client.post(path, json=body,
                            headers={"Authorization": "Bearer " + tokens[actor]})
            assert r.status_code == expected, (path, r.status_code, r.text)
            return r.json()

        mid = post("/api/v1/meetings", {"title": "acceptance mock"}, 201)["meeting_id"]

        # ---- S1 capture: synthetic PCM stands in for a real mic recording ----
        pcm = bytes(640)  # one 20 ms frame of silence
        ev["S1_capture"] = {"source": "synthetic", "pcm_bytes": len(pcm),
                            "format": "16k mono s16le", "note": "非真人录音"}

        # ---- S2 ASR: uplink WS -> FunASR stub -> utterance.final ----
        mic_token = post(f"/api/v1/meetings/{mid}/devices/bench_mic/pair", expected=201)["media_token"]
        config = {"schema_version": "1.0", "type": "audio.start", "session_id": str(uuid4()),
                  "meeting_id": mid, "device_id": "bench_mic", "stream_id": "bench_mic",
                  "stream_key": 1, "direction": "uplink", "purpose": "onsite_voice",
                  "command_id": None, "sample_rate_hz": 16000, "channels": 1,
                  "encoding": "s16le", "frame_ms": 20}
        post(f"/api/bench/meetings/{mid}/media-bindings",
             {"config": config, "speaker_id": "remote_1", "channel": "remote", "start_ms": 100}, 201)
        with client.websocket_connect("/device/v1/audio",
                                      headers={"Authorization": "Bearer " + mic_token}) as ws:
            ws.send_json(config)
            assert ws.receive_json()["accepted"] is True
            ws.send_bytes(encode_frame(1, 0, 0, pcm))
            assert ws.receive_json()["sample_end"] == 320
            ws.send_json({"type": "audio.end", "session_id": config["session_id"],
                          "stream_key": 1, "reason": "completed", "command_id": None})
            final = ws.receive_json()
            assert final["type"] == "utterance.final", final
            utterance_id = final["event"]["payload"]["utterance_id"]
            assert ws.receive_json()["type"] == "audio.closed"
        ev["S2_asr"] = {"text_len": len(asr.pcm), "utterance_id": utterance_id,
                        "asr_mode": asr.mode, "note": "StubASR，非真实 FunASR"}

        # ---- S3 analyze: qwen stub -> completed candidate ----
        job = post(f"/api/v1/meetings/{mid}/analysis", {"evidence_ids": [utterance_id]}, 202)
        result = None
        for _ in range(200):
            result = runtime.job(mid, job["job_id"])
            if result["status"] in {"completed", "failed"}:
                break
            time.sleep(0.02)
        assert result and result["status"] == "completed", result
        intervention = result["result"]["intervention"]
        ev["S3_analyze"] = {"job_status": result["status"],
                            "intervention_id": intervention["intervention_id"],
                            "model": "stub(fake-analyzer)", "note": "非真实 qwen-plus"}

        # ---- S4 confirm: owner (remote_1) confirms on the web -> command queued ----
        decision = post(f"/api/v1/meetings/{mid}/interventions/{intervention['intervention_id']}/decision",
                        {"decision": "confirm", "expected_revision": 1}, 202, "remote_1")
        command_id = decision["command"]["command_id"]
        ev["S4_confirm"] = {"command_id": command_id, "confirmed_by": "remote_1",
                            "receipts_before_play": decision["receipts"],
                            "note": "测试身份，非真实账号本人确认"}

        # ---- S5 playback: robot speaker drains frames -> completed receipt ----
        spk_token = post(f"/api/v1/meetings/{mid}/devices/host_speaker_test/pair",
                         expected=201)["media_token"]
        boot = str(uuid4())
        with client.websocket_connect("/device/v1/playback",
                                      headers={"Authorization": "Bearer " + spk_token}) as ws:
            ws.send_json({"command_id": command_id, "device_id": "host_speaker_test",
                          "boot_id": boot, "safe_pause": True})
            start = ws.receive_json()
            assert start["type"] == "audio.start", start
            ws.send_json({"type": "audio.ready", "session_id": start["session_id"],
                          "stream_key": 1, "accepted": True, "error_code": None})

            def receipt(status):
                return {"command_id": command_id, "target_device_id": "host_speaker_test",
                        "boot_id": boot, "status": status, "error_code": None}

            ws.send_json(receipt("accepted"))
            ws.send_json(receipt("started"))
            frames = 0
            for end in (320, 640):
                assert len(ws.receive_bytes()) == 664
                ws.send_json({"type": "audio.ack", "sample_end": end})
                frames += 1
            assert ws.receive_json()["type"] == "audio.end"
            ws.send_json(receipt("completed"))
            assert ws.receive_json()["type"] == "playback.closed"
        final_state = runtime.command(command_id)["state"]
        ev["S5_playback"] = {"frames_acked": frames, "final_command_state": final_state,
                             "sink": "host_speaker_test", "note": "台架播放器，非真实机器人出声"}

        # ---- S6 response tracking: onsite response + viewpoint map ----
        post(f"/api/v1/meetings/{mid}/utterances",
             {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "onsite_1",
              "channel": "onsite", "start_ms": 5000, "end_ms": 7000,
              "text": "现场已回应该观点。", "final": True, "revision": 1}, 201)
        post(f"/api/v1/meetings/{mid}/viewpoint-map", {}, expected=202)
        vmap = client.get(f"/api/v1/meetings/{mid}/viewpoint-map",
                          headers={"Authorization": "Bearer " + tokens["operator"]}).json()
        statuses = [v.get("response_status") for v in vmap.get("viewpoints", [])]
        ev["S6_response_tracking"] = {"viewpoint_count": len(vmap.get("viewpoints", [])),
                                      "response_statuses": statuses,
                                      "note": "mock 不验证真实回应检测；状态以账本为准"}
    finally:
        _drain_loop()
        client.__exit__(None, None, None)
        tmp.cleanup()
    return ev
