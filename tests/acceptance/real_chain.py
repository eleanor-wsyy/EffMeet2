"""Real-mode execution paths that do not need a robot or a cloud model key.

S1 capture accepts either a supplied 16 kHz mono WAV (`EFFMEET_ACC_MIC` is a
path) or records from the host microphone with sounddevice (`EFFMEET_ACC_MIC=1`).
S2 sends that PCM through the REAL controller/relay WebSocket with a REAL
FunASR adapter. Stages that still need qwen/robot/real accounts stay NOT_RUN in
harness.py; this module never upgrades them.
"""
from __future__ import annotations

import math
import os
import struct
import tempfile
import time
import wave
from pathlib import Path
from uuid import uuid4

from services.controller.app import create_app
from services.relay.protocol import encode_frame


class NotRun(RuntimeError):
    """A real dependency is unavailable; the stage stays NOT_RUN."""


def pcm_metrics(pcm: bytes) -> dict:
    if not pcm or len(pcm) % 2:
        raise ValueError("PCM must be non-empty 16-bit samples")
    values = [v[0] for v in struct.iter_unpack('<h', pcm)]
    samples = len(values)
    duration_ms = samples / 16.0
    if not 200 <= duration_ms <= 30000:
        raise ValueError("PCM must be 0.2..30 seconds")
    rms = math.sqrt(sum(v * v for v in values) / samples)
    dbfs = 20 * math.log10(rms / 32768.0) if rms else float('-inf')
    if dbfs < -50:
        raise ValueError("PCM is silent or too quiet (below -50 dBFS)")
    return {"samples": samples, "duration_ms": round(duration_ms, 1),
            "rms_dbfs": round(dbfs, 1), "format": "16k mono s16le"}


def _read_wav(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                wav.getcomptype()) != (1, 2, 16000, "NONE"):
            raise ValueError("WAV must be 16 kHz mono 16-bit PCM")
        pcm = wav.readframes(wav.getnframes())
    return pcm


def _record_microphone(seconds: float) -> bytes:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise NotRun("未安装 sounddevice；安装 requirements-media.txt 或提供真实 WAV 路径") from exc
    try:
        sd.check_input_settings(samplerate=16000, channels=1, dtype='int16')
        data = sd.rec(int(seconds * 16000), samplerate=16000, channels=1, dtype='int16')
        sd.wait()
    except Exception as exc:
        raise NotRun("本机没有可用的录音输入设备（" + type(exc).__name__ + "）") from exc
    return data.tobytes()


def _obtain_pcm(gate: str, gate_name: str, seconds_var: str) -> tuple[bytes, str]:
    path = Path(gate)
    if path.suffix.lower() in {".wav"} and path.is_file():
        return _read_wav(path), "provided_wav"
    if gate in {"1", "true", "yes", "on"}:
        seconds = float(os.environ.get(seconds_var, "3"))
        if not 0.2 <= seconds <= 30:
            raise ValueError(seconds_var + " must be 0.2..30")
        return _record_microphone(seconds), "microphone"
    if path.suffix.lower() in {".wav"}:
        raise ValueError(gate_name + " points to a missing WAV file")
    raise NotRun(gate_name + " 需为 1（录麦克风）或真实 16k mono WAV 路径")


def capture(context: dict) -> dict:
    """S1: obtain real PCM and validate format/duration/level."""
    pcm, source = _obtain_pcm(os.environ.get("EFFMEET_ACC_MIC", "").strip(),
                              "EFFMEET_ACC_MIC", "EFFMEET_ACC_MIC_SECONDS")
    metrics = pcm_metrics(pcm)
    context["pcm"] = pcm
    return {"source": source, **metrics, "note": "真人录音需由执行者确认；本检查只验证格式/时长/电平"}


def ingest_pcm(client, meeting: str, pcm: bytes, *, speaker_id: str, channel: str,
               headers: dict) -> dict:
    """Send PCM through the real media WS of an existing app/meeting."""
    pair = client.post(f"/api/v1/meetings/{meeting}/devices/bench_mic/pair",
                       headers=headers).json()
    media_token = pair["media_token"]
    config = {
        "schema_version": "1.0", "type": "audio.start", "session_id": str(uuid4()),
        "meeting_id": meeting, "device_id": "bench_mic", "stream_id": "bench_mic",
        "stream_key": 1, "direction": "uplink", "purpose": "onsite_voice",
        "command_id": None, "sample_rate_hz": 16000, "channels": 1,
        "encoding": "s16le", "frame_ms": 20,
    }
    client.post(f"/api/bench/meetings/{meeting}/media-bindings",
                json={"config": config, "speaker_id": speaker_id,
                      "channel": channel, "start_ms": 0},
                headers=headers).raise_for_status()
    with client.websocket_connect(
            "/device/v1/audio",
            headers={"Authorization": "Bearer " + media_token}) as ws:
        ws.send_json(config)
        ready = ws.receive_json()
        if not ready.get("accepted"):
            raise RuntimeError("media binding rejected: " + str(ready))
        for seq, offset in enumerate(range(0, len(pcm), 640)):
            ws.send_bytes(encode_frame(1, seq, offset // 2, pcm[offset:offset + 640]))
            ack = ws.receive_json()
            if ack.get("type") != "audio.ack":
                raise RuntimeError("unexpected media response: " + str(ack))
        ws.send_json({"type": "audio.end", "session_id": config["session_id"],
                      "stream_key": 1, "reason": "completed", "command_id": None})
        final = ws.receive_json()
        if final.get("type") != "utterance.final":
            raise RuntimeError("ASR did not produce utterance.final: " + str(final))
        return final["event"]["payload"]


def transcribe_and_ingest(pcm: bytes, asr) -> dict:
    """S2: send PCM through the real media WS; return the ledgered utterance."""
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory(prefix="effmeet-acc-") as tmp:
        app = create_app(Path(tmp) / "acceptance.sqlite3", bench=True, asr=asr)
        with TestClient(app) as client:
            tokens = {p["actor"]: p["token"]
                      for p in client.get("/api/demo/session").json()["profiles"]}
            headers = {"Authorization": "Bearer " + tokens["operator"]}
            meeting = client.post("/api/v1/meetings", json={"title": "acceptance real ASR"},
                                  headers=headers).json()["meeting_id"]
            payload = ingest_pcm(client, meeting, pcm, speaker_id="onsite_1",
                                 channel="onsite", headers=headers)
    return {"text": payload["text"], "text_len": len(payload["text"]),
            "utterance_id": payload["utterance_id"], "asr_mode": getattr(asr, "mode", "unknown"),
            "meeting_id": meeting}


def asr(context: dict) -> dict:
    """S2: real FunASR adapter over a real WebSocket."""
    pcm = context.get("pcm")
    if not pcm:
        raise NotRun("S1 未产出 PCM，无法执行真实 ASR")
    from services.relay.asr import FunASR
    url = os.environ.get("FUNASR_WS_URL", "").strip()
    if not url:
        raise NotRun("未设置 FUNASR_WS_URL")
    adapter = FunASR(url)
    try:
        evidence = transcribe_and_ingest(pcm, adapter)
    except Exception as exc:
        raise RuntimeError(f"真实 ASR 链路失败：{type(exc).__name__}: {exc}") from exc
    if not evidence["text"].strip():
        raise RuntimeError("真实 ASR 返回空文本")
    return evidence


class _StubModel:
    mode = "real"

    def analyze(self, evidence, status):
        from services.controller.fakes import FakeAnalyzer
        return FakeAnalyzer().analyze(evidence, "possibly_unresponded")


def analyze(context: dict) -> dict:
    """S3: real qwen-plus analysis through the bench worker (key from env only)."""
    key = os.environ.get("QWEN_API_KEY", "").strip()
    analyzer = context.get("analyzer")
    if analyzer is None:
        if not key:
            raise NotRun("未设置 QWEN_API_KEY")
        from services.controller.qwen_client import create_analyzer
        analyzer = create_analyzer()
    if getattr(analyzer, "mode", "") != "real":
        raise NotRun("分析器不是 real 模式")
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory(prefix="effmeet-s3-") as tmp:
        app = create_app(Path(tmp) / "s3.sqlite3", bench=True, analyzer=analyzer)
        with TestClient(app) as client:
            tokens = {p["actor"]: p["token"]
                      for p in client.get("/api/demo/session").json()["profiles"]}
            headers = {"Authorization": "Bearer " + tokens["operator"]}
            meeting = client.post("/api/v1/meetings", json={"title": "S3 real qwen"},
                                  headers=headers).json()["meeting_id"]
            ids = []
            for speaker, channel, text in [
                ("onsite_2", "onsite", "我觉得箱体用折叠的，运输方便。"),
                ("onsite_1", "onsite", "折叠的结构强度够不够？回收箱会被撞。"),
                ("remote_1", "remote", "我说个事——满溢检测的话，用重量传感器比摄像头便宜很多，而且不用处理隐私问题。"),
                ("onsite_2", "onsite", "折叠的那个连接件可以用卡扣，拆装很方便。"),
                ("onsite_1", "onsite", "对，而且折叠的模具成本高。"),
            ]:
                uid = str(uuid4())
                response = client.post(f"/api/v1/meetings/{meeting}/utterances", headers=headers, json={
                    "utterance_id": uid, "stream_id": "manual_" + channel,
                    "speaker_id": speaker, "channel": channel, "start_ms": 0,
                    "end_ms": 1000, "text": text, "final": True, "revision": 1,
                })
                if response.status_code not in {200, 201}:
                    raise RuntimeError("utterance rejected: " + response.text)
                ids.append(uid)
            job = client.post(f"/api/v1/meetings/{meeting}/analysis",
                              json={"evidence_ids": ids}, headers=headers).json()
            runtime = app.state.bench
            result = None
            for _ in range(600):
                result = runtime.job(meeting, job["job_id"])
                if result["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.05)
            if not result or result["status"] != "completed":
                raise RuntimeError("qwen job failed: " + str(result))
            analysis = result["result"]["analysis"]
            intervention = result["result"].get("intervention")
            if analysis["owner_speaker_id"] != "remote_1":
                raise RuntimeError("unexpected owner: " + analysis["owner_speaker_id"])
            if analysis["status"] not in {"responded", "possibly_unresponded", "uncertain"}:
                raise RuntimeError("invalid status: " + analysis["status"])
            if set(analysis["evidence_ids"]) != set(ids):
                raise RuntimeError("evidence IDs changed")
            if len(analysis["proposed_text"]) > 80:
                raise RuntimeError("proposed_text too long")
    return {
        "meeting_id": meeting,
        "status": analysis["status"],
        "owner_speaker_id": analysis["owner_speaker_id"],
        "evidence_ids": analysis["evidence_ids"],
        "proposed_text": analysis["proposed_text"],
        "reason_len": len(analysis["reason"]),
        "model": analysis["model"],
        "intervention_id": intervention["intervention_id"] if intervention else None,
        "api_key_source": "environment",
    }


def response_tracking(context: dict) -> dict:
    """S6: real onsite audio/ASR + real response verification + viewpoint map.

    The candidate analysis and owner confirmation use a local stub and the
    remote_1 test identity. That is enough for the response-tracking software
    path, but it is NOT a full human/account acceptance; the evidence says so.
    """
    pcm, source = _obtain_pcm(os.environ.get("EFFMEET_ACC_ONSITE_MIC", "").strip(),
                              "EFFMEET_ACC_ONSITE_MIC", "EFFMEET_ACC_ONSITE_SECONDS")
    asr = context.get("asr")
    if asr is None:
        from services.relay.asr import FunASR
        url = os.environ.get("FUNASR_WS_URL", "").strip()
        if not url:
            raise NotRun("未设置 FUNASR_WS_URL")
        asr = FunASR(url)
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory(prefix="effmeet-s6-") as tmp:
        app = create_app(Path(tmp) / "s6.sqlite3", bench=True, asr=asr,
                         analyzer=_StubModel())
        with TestClient(app) as client:
            tokens = {p["actor"]: p["token"]
                      for p in client.get("/api/demo/session").json()["profiles"]}
            operator = {"Authorization": "Bearer " + tokens["operator"]}
            remote = {"Authorization": "Bearer " + tokens["remote_1"]}
            meeting = client.post("/api/v1/meetings", json={"title": "S6 response tracking"},
                                  headers=operator).json()["meeting_id"]
            remote_uid = str(uuid4())
            response = client.post(f"/api/v1/meetings/{meeting}/utterances", headers=operator, json={
                "utterance_id": remote_uid, "stream_id": "manual_remote",
                "speaker_id": "remote_1", "channel": "remote", "start_ms": 0,
                "end_ms": 1000, "text": "满溢检测用重量传感器比摄像头便宜很多。",
                "final": True, "revision": 1,
            })
            if response.status_code not in {200, 201}:
                raise RuntimeError("remote utterance rejected: " + response.text)
            job = client.post(f"/api/v1/meetings/{meeting}/analysis",
                              json={"evidence_ids": [remote_uid]}, headers=operator).json()
            runtime = app.state.bench
            result = None
            for _ in range(200):
                result = runtime.job(meeting, job["job_id"])
                if result["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.02)
            if not result or result["status"] != "completed":
                raise RuntimeError("stub analysis failed: " + str(result))
            intervention = result["result"]["intervention"]
            decision = client.post(
                f"/api/v1/meetings/{meeting}/interventions/{intervention['intervention_id']}/decision",
                json={"decision": "confirm", "expected_revision": 1}, headers=remote)
            if decision.status_code != 202:
                raise RuntimeError("confirm failed: " + decision.text)

            payload = ingest_pcm(client, meeting, pcm, speaker_id="onsite_1",
                                 channel="onsite", headers=operator)
            tracking = client.get(f"/api/bench/meetings/{meeting}/response-tracking",
                                  headers=remote).json()
            claim = next((c for c in tracking["claims"]
                          if c["claim_id"] == intervention["claim_id"]), None)
            if not claim:
                raise RuntimeError("claim not found in response tracking")
            review_ids = {u["utterance_id"] for u in claim["onsite_to_review"]}
            if payload["utterance_id"] not in review_ids:
                raise RuntimeError("onsite response is not later than the source view")
            verified = client.post(
                f"/api/bench/meetings/{meeting}/claims/{claim['claim_id']}/response-verification",
                json={"response_utterance_ids": [payload["utterance_id"]]}, headers=remote)
            if verified.status_code != 200:
                raise RuntimeError("response verification failed: " + verified.text)
            client.post(f"/api/v1/meetings/{meeting}/viewpoint-map", json={},
                        headers=operator).raise_for_status()
            vmap = client.get(f"/api/v1/meetings/{meeting}/viewpoint-map",
                              headers=operator).json()
            viewpoint = next((v for v in vmap["viewpoints"] if remote_uid in v["evidence_ids"]), None)
            if not viewpoint or viewpoint["response_status"] != "responded":
                raise RuntimeError("viewpoint map did not mark the response: " + str(viewpoint))
    return {
        "meeting_id": meeting,
        "onsite_source": source,
        "onsite_text": payload["text"],
        "onsite_utterance_id": payload["utterance_id"],
        "asr_mode": getattr(asr, "mode", "unknown"),
        "claim_id": claim["claim_id"],
        "verification_status": "human_verified",
        "viewpoint_response_status": viewpoint["response_status"],
        "analysis": "stub(FakeAnalyzer)",
        "owner": "remote_1(test identity)",
        "note": "现场音频与 ASR 真实；候选分析/本人确认使用 stub 与测试身份，不是完整人工验收",
    }
