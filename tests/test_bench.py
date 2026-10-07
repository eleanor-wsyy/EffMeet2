"""Bench regression tests: real protocol; explicitly synthetic ASR/TTS/model."""
import asyncio
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from services.controller.app import create_app
from services.controller.contracts import DemoError
from services.controller.fakes import FakeAnalyzer
from services.controller.qwen_client import QwenAnalyzer
from services.relay.protocol import Decoder, ProtocolError, encode_frame


class StubASR:
    mode = "mock"
    async def transcribe(self, pcm, sid):
        self.pcm = pcm
        return "先验证草图。"


class StubTTS:
    def synthesize(self, text):
        return bytes(1280)


class StubModel:
    mode = "real"  # Exercise the external-adapter path, but output explicitly says mock.
    def analyze(self, evidence, status):
        return FakeAnalyzer().analyze(evidence, "possibly_unresponded")


class ProtocolTests(unittest.TestCase):
    def test_roundtrip_duplicate_gap(self):
        d = Decoder(1)
        frame = encode_frame(1, 0, 0, bytes(640))
        self.assertEqual(len(frame), 664)
        self.assertEqual(d.feed(frame), (bytes(640), "ok"))
        self.assertEqual(d.feed(frame), (b"", "duplicate"))
        self.assertEqual(d.feed(encode_frame(1, 2, 640, bytes(200))), (bytes(840), "gap"))
        self.assertEqual(d.samples, 740)

    def test_invalid_header_stream_length_order(self):
        valid = encode_frame(1, 0, 0, bytes(640))
        for frame in [bytes(640), valid[:-1], b"BAD!" + valid[4:], encode_frame(2, 0, 0, bytes(640)),
                      encode_frame(1, 0, 10, bytes(640)), encode_frame(1, 20, 6400, bytes(640))]:
            with self.subTest(length=len(frame)), self.assertRaises(ProtocolError):
                Decoder(1).feed(frame)


class BenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.asr = StubASR()
        self.app = create_app(Path(self.tmp.name) / "bench.db", bench=True, asr=self.asr,
                              tts=StubTTS(), analyzer=StubModel())
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.tokens = {p["actor"]: p["token"] for p in self.client.get("/api/demo/session").json()["profiles"]}
        self.mid = self.post("/api/v1/meetings", {"title": "synthetic bench"}, 201)["meeting_id"]
        self.runtime = self.app.state.bench

    def tearDown(self):
        # Explicitly close any pending asyncio tasks before TestClient cleanup
        # to prevent "Event loop is closed" errors on Python 3.13+
        try:
            # Python 3.13+: avoid DeprecationWarning from get_event_loop()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop.is_running():
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            if not loop.is_closed():
                loop.close()
        except RuntimeError:
            pass  # No event loop in this thread
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def post(self, path, body=None, expected=200, actor="operator"):
        response = self.client.post(path, json=body, headers={"Authorization": "Bearer " + self.tokens[actor]})
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def bind(self):
        token = self.post(f"/api/v1/meetings/{self.mid}/devices/bench_mic/pair", expected=201)["media_token"]
        config = {"schema_version": "1.0", "type": "audio.start", "session_id": str(uuid4()),
            "meeting_id": self.mid, "device_id": "bench_mic", "stream_id": "bench_mic",
            "stream_key": 1, "direction": "uplink", "purpose": "onsite_voice", "command_id": None,
            "sample_rate_hz": 16000, "channels": 1, "encoding": "s16le", "frame_ms": 20}
        self.post(f"/api/bench/meetings/{self.mid}/media-bindings",
                  {"config": config, "speaker_id": "remote_1", "channel": "remote", "start_ms": 100}, 201)
        return config, {"Authorization": "Bearer " + token}

    def utterance(self, text="先验证草图。"):
        u = {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "remote_1",
            "channel": "remote", "start_ms": 0, "end_ms": 1000, "text": text, "final": True, "revision": 1}
        self.post(f"/api/v1/meetings/{self.mid}/utterances", u, 201)
        return u

    def candidate(self):
        u = self.utterance()
        job = self.post(f"/api/v1/meetings/{self.mid}/analysis", {"evidence_ids": [u["utterance_id"]]}, 202)
        for _ in range(100):
            result = self.runtime.job(self.mid, job["job_id"])
            if result["status"] in {"completed", "failed"}:
                break
            time.sleep(.02)
        self.assertEqual(result["status"], "completed", result)
        return result["result"]["intervention"]

    def command(self):
        c = self.candidate()
        result = self.post(f"/api/v1/meetings/{self.mid}/interventions/{c['intervention_id']}/decision",
            {"decision": "confirm", "expected_revision": 1}, 202, "remote_1")
        self.assertEqual(result["receipts"], [])
        token = self.post(f"/api/v1/meetings/{self.mid}/devices/host_speaker_test/pair", expected=201)["media_token"]
        return result["command"]["command_id"], {"Authorization": "Bearer " + token}

    def test_uplink_final_binding_and_no_reuse(self):
        config, headers = self.bind()
        with self.client.websocket_connect("/device/v1/audio", headers=headers) as ws:
            ws.send_json(config)
            self.assertTrue(ws.receive_json()["accepted"])
            frame = encode_frame(1, 0, 0, bytes(640))
            ws.send_bytes(frame)
            self.assertEqual(ws.receive_json()["sample_end"], 320)
            ws.send_bytes(frame)
            self.assertEqual(ws.receive_json()["diagnostic"], "duplicate")
            ws.send_json({"type": "audio.end", "session_id": config["session_id"], "stream_key": 1,
                          "reason": "completed", "command_id": None})
            event = ws.receive_json()["event"]
            self.assertEqual(event["mode"], "mock")
            self.assertEqual(event["payload"]["channel"], "remote")
            self.assertEqual(event["payload"]["end_ms"], 120)
            self.assertEqual(ws.receive_json()["type"], "audio.closed")
        self.assertEqual(len(self.asr.pcm), 640)
        with self.client.websocket_connect("/device/v1/audio", headers=headers) as ws:
            ws.send_json(config)
            self.assertEqual(ws.receive_json()["error_code"], "INVALID_SESSION")

    def test_bad_token_and_binding_mismatch(self):
        config, headers = self.bind()
        with self.client.websocket_connect("/device/v1/audio", headers={"Authorization": "Bearer bad"}) as ws:
            ws.send_json(config)
            self.assertEqual(ws.receive_json()["error_code"], "INVALID_MEDIA_TOKEN")
        with self.client.websocket_connect("/device/v1/audio", headers=headers) as ws:
            ws.send_json({**config, "stream_key": 2})
            self.assertEqual(ws.receive_json()["error_code"], "INVALID_SESSION")

    def test_missing_asr_is_visible(self):
        app = create_app(Path(self.tmp.name) / "missing.db", bench=True)
        self.assertIsNone(app.state.bench.tts)

    def test_job_idempotency_and_readable_while_model_running(self):
        entered, release = threading.Event(), threading.Event()
        class SlowModel(StubModel):
            def analyze(self, evidence, status):
                entered.set()
                release.wait(3)
                return super().analyze(evidence, status)
        self.runtime.analyzer = SlowModel()
        u = self.utterance()
        body = {"evidence_ids": [u["utterance_id"]]}
        one = self.post(f"/api/v1/meetings/{self.mid}/analysis", body, 202)
        try:
            self.assertTrue(entered.wait(2))
            two = self.post(f"/api/v1/meetings/{self.mid}/analysis", body, 202)
            self.assertEqual(one["job_id"], two["job_id"])
            self.utterance("模型运行时新发言仍可写入。")
        finally:
            release.set()
        for _ in range(100):
            job = self.runtime.job(self.mid, one["job_id"])
            if job["status"] == "failed":
                break
            time.sleep(.02)
        self.assertEqual(job["error_code"], "CONTEXT_CHANGED")

    def play_start(self, ws, cid):
        boot = str(uuid4())
        ws.send_json({"command_id": cid, "device_id": "host_speaker_test", "boot_id": boot, "safe_pause": True})
        config = ws.receive_json()
        self.assertEqual(config["type"], "audio.start", config)
        ws.send_json({"type": "audio.ready", "session_id": config["session_id"], "stream_key": 1,
                      "accepted": True, "error_code": None})
        def receipt(status):
            return {"command_id": cid, "target_device_id": "host_speaker_test", "boot_id": boot,
                    "status": status, "error_code": None}
        ws.send_json(receipt("accepted"))
        ws.send_json(receipt("started"))
        return receipt

    def test_playback_requires_drain_receipt_and_rejects_replay(self):
        cid, headers = self.command()
        with self.client.websocket_connect("/device/v1/playback", headers=headers) as ws:
            receipt = self.play_start(ws, cid)
            for end in [320, 640]:
                self.assertEqual(len(ws.receive_bytes()), 664)
                ws.send_json({"type": "audio.ack", "sample_end": end})
            self.assertEqual(ws.receive_json()["type"], "audio.end")
            self.assertEqual(self.runtime.command(cid)["state"], "playing")
            ws.send_json(receipt("completed"))
            self.assertEqual(ws.receive_json()["type"], "playback.closed")
        self.assertEqual(self.runtime.command(cid)["state"], "completed")
        with self.client.websocket_connect("/device/v1/playback", headers=headers) as ws:
            ws.send_json({"command_id": cid, "device_id": "host_speaker_test", "boot_id": str(uuid4()), "safe_pause": True})
            self.assertEqual(ws.receive_json()["error_code"], "COMMAND_NOT_QUEUED")

    def test_stop_cancels_outstanding_frame(self):
        cid, headers = self.command()
        with self.client.websocket_connect("/device/v1/playback", headers=headers) as ws:
            self.play_start(ws, cid)
            ws.receive_bytes()
            self.post(f"/api/bench/commands/{cid}/stop", expected=403, actor="remote_2")
            self.post(f"/api/bench/commands/{cid}/stop", expected=202, actor="remote_1")
            self.assertEqual(ws.receive_json()["reason"], "stopped")
            self.assertEqual(ws.receive_json()["error_code"], "CANCELLED")
        self.assertEqual(json.loads(self.runtime.command(cid)["receipts"])[-1]["error_code"], "CANCELLED")

    def test_restart_never_replays_queued_command(self):
        cid, _ = self.command()
        self.runtime.recover()
        self.assertEqual(self.runtime.command(cid)["state"], "failed")

    def test_events_resume(self):
        u = self.utterance()
        with self.client.websocket_connect(f"/api/v1/meetings/{self.mid}/events") as ws:
            ws.send_json({"token": self.tokens["remote_1"], "after_seq": 1})
            e = ws.receive_json()
            self.assertEqual(e["seq"], 2)
            self.assertEqual(e["payload"]["utterance_id"], u["utterance_id"])


class QwenTests(unittest.TestCase):
    def test_response_requires_explicit_valid_evidence(self):
        q = QwenAnalyzer(api_key="synthetic")
        remote = {"utterance_id": str(uuid4()), "speaker_id": "remote_1", "channel": "remote", "text": "建议"}
        onsite = {"utterance_id": str(uuid4()), "speaker_id": "onsite_1", "channel": "onsite", "text": "同意"}
        base = {"status": "responded", "proposed_text": "", "reason": "回复", "response_utterance_ids": [onsite["utterance_id"]]}
        self.assertEqual(q._parse_analysis(json.dumps(base), [remote, onsite])["response_utterance_ids"], [onsite["utterance_id"]])
        for bad in [[], {**base, "response_utterance_ids": []}, {**base, "response_utterance_ids": [str(uuid4())]},
                    {**base, "status": "possibly_unresponded"}, {**base, "proposed_text": 3}]:
            with self.subTest(bad=bad), self.assertRaises(DemoError):
                q._parse_analysis(json.dumps(bad), [remote, onsite])


if __name__ == "__main__":
    unittest.main()
