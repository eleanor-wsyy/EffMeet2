import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from tests.acceptance.harness import E2EAcceptanceHarness, FAIL, NOT_RUN, PASS
from tests.acceptance.real_chain import _StubModel, analyze, response_tracking, transcribe_and_ingest


def write_wav(path: Path, *, seconds: float = 0.5, amplitude: int = 3000) -> None:
    frames = b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 440 * i / 16000)))
        for i in range(int(seconds * 16000))
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(frames)


class RealChainTests(unittest.TestCase):
    def test_s1_accepts_a_valid_wav_and_leaves_keyed_stages_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "real.wav"
            write_wav(path)
            with patch.dict(os.environ, {"EFFMEET_ACC_MIC": str(path)}, clear=True):
                results = {r.stage_id: r for r in E2EAcceptanceHarness("real").run()}
        self.assertEqual(results["S1_capture"].status, PASS)
        self.assertEqual(results["S1_capture"].evidence["source"], "provided_wav")
        self.assertEqual(results["S1_capture"].evidence["format"], "16k mono s16le")
        self.assertEqual(results["S2_asr"].status, NOT_RUN)
        for stage in ("S3_analyze", "S4_confirm", "S5_playback", "S6_response_tracking"):
            self.assertEqual(results[stage].status, NOT_RUN)

    def test_s1_rejects_silence_instead_of_passing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.wav"
            write_wav(path, amplitude=0)
            with patch.dict(os.environ, {"EFFMEET_ACC_MIC": str(path)}, clear=True):
                results = {r.stage_id: r for r in E2EAcceptanceHarness("real").run()}
        self.assertEqual(results["S1_capture"].status, FAIL)
        self.assertIn("silent", results["S1_capture"].reason.lower())

    def test_s1_reports_not_run_for_an_unusable_gate(self):
        with patch.dict(os.environ, {"EFFMEET_ACC_MIC": "not-a-wav"}, clear=True):
            results = {r.stage_id: r for r in E2EAcceptanceHarness("real").run()}
        self.assertEqual(results["S1_capture"].status, NOT_RUN)
        self.assertIn("EFFMEET_ACC_MIC", results["S1_capture"].reason)

    def test_s2_ingests_pcm_through_the_real_media_ws_with_a_stub_asr(self):
        class StubASR:
            mode = "mock"

            async def transcribe(self, pcm, session_id):
                self.pcm = pcm
                return "真实链路转写文本"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "real.wav"
            write_wav(path)
            with wave.open(str(path), "rb") as wav:
                pcm = wav.readframes(wav.getnframes())
        asr = StubASR()
        evidence = transcribe_and_ingest(pcm, asr)
        self.assertEqual(evidence["text"], "真实链路转写文本")
        self.assertTrue(evidence["utterance_id"])
        self.assertEqual(evidence["asr_mode"], "mock")
        self.assertEqual(len(asr.pcm), len(pcm))

    def test_s3_real_worker_path_with_injected_analyzer(self):
        evidence = analyze({"analyzer": _StubModel()})
        self.assertEqual(evidence["owner_speaker_id"], "remote_1")
        self.assertIn(evidence["status"], {"responded", "possibly_unresponded", "uncertain"})
        self.assertTrue(evidence["evidence_ids"])
        self.assertIsNotNone(evidence["intervention_id"])
        self.assertEqual(evidence["api_key_source"], "environment")

    def test_s6_real_controller_tracks_onsite_response(self):
        class StubASR:
            mode = "mock"

            async def transcribe(self, pcm, session_id):
                return "现场回应：重量传感器确实更便宜。"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "onsite.wav"
            write_wav(path)
            with patch.dict(os.environ, {"EFFMEET_ACC_ONSITE_MIC": str(path)}, clear=True):
                evidence = response_tracking({"asr": StubASR()})
        self.assertEqual(evidence["onsite_text"], "现场回应：重量传感器确实更便宜。")
        self.assertEqual(evidence["verification_status"], "human_verified")
        self.assertEqual(evidence["viewpoint_response_status"], "responded")
        self.assertEqual(evidence["analysis"], "stub(FakeAnalyzer)")
        self.assertIn("test identity", evidence["owner"])
