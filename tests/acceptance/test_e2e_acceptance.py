"""End-to-end acceptance harness tests.

Runnable anywhere (no hardware):
  - mock mode proves the harness wiring against the real software stack.
  - real mode without gates must report NOT_RUN for every stage (never PASS).

Gated real run (requires hardware + services + EFFMEET_ACCEPTANCE_REAL=1):
  - asserts the discipline that no stage falsely reports PASS without evidence.
"""
import os
import unittest

from .harness import (MOCK_OK, NOT_RUN, PASS, STAGES, E2EAcceptanceHarness)

REAL_ENV_VARS = ["EFFMEET_ACC_MIC", "FUNASR_WS_URL", "QWEN_API_KEY",
                 "EFFMEET_ACC_WEB_OWNER", "EFFMEET_ACC_ROBOT", "EFFMEET_ACC_ONSITE_MIC"]


class MockWiringTests(unittest.TestCase):
    def test_mock_chain_runs_all_stages(self):
        results = E2EAcceptanceHarness(mode="mock").run()
        self.assertEqual([r.stage_id for r in results], [s.stage_id for s in STAGES])
        for r in results:
            self.assertEqual(r.status, MOCK_OK,
                             f"{r.stage_id} should be MOCK_OK in mock mode, got {r.status}")
            # Mock must never masquerade as real acceptance.
            self.assertNotEqual(r.status, PASS)

    def test_mock_evidence_shows_completed_playback(self):
        results = {r.stage_id: r for r in E2EAcceptanceHarness(mode="mock").run()}
        # The software chain really drove a command to completed via the playback WS.
        self.assertEqual(results["S5_playback"].evidence.get("final_command_state"), "completed")
        self.assertEqual(results["S5_playback"].evidence.get("frames_acked"), 2)
        self.assertIn("utterance_id", results["S2_asr"].evidence)
        self.assertIn("intervention_id", results["S3_analyze"].evidence)


class RealGateTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in REAL_ENV_VARS}
        for k in REAL_ENV_VARS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_real_mode_without_gates_is_not_run(self):
        results = E2EAcceptanceHarness(mode="real").run()
        self.assertEqual(len(results), len(STAGES))
        for r in results:
            self.assertEqual(r.status, NOT_RUN,
                             f"{r.stage_id} must be NOT_RUN without real deps, got {r.status}")
            self.assertTrue(r.reason.startswith("NOT_RUN"), r.reason)
            self.assertNotEqual(r.status, PASS)  # never a fake PASS


@unittest.skipUnless(os.environ.get("EFFMEET_ACCEPTANCE_REAL") == "1",
                     "real-machine acceptance gated: set EFFMEET_ACCEPTANCE_REAL=1 "
                     "with hardware + FunASR + qwen + LiveKit ready")
class RealChainTests(unittest.TestCase):
    def test_real_chain_never_fakes_pass(self):
        results = E2EAcceptanceHarness(mode="real").run()
        for r in results:
            # Until the physical execution path is implemented, a gated real run
            # still reports NOT_RUN; the invariant is that PASS requires evidence.
            if r.status == PASS:
                self.assertTrue(r.evidence, f"{r.stage_id} reported PASS without evidence")
            else:
                self.assertIn(r.status, {NOT_RUN, "FAIL"})


if __name__ == "__main__":
    unittest.main()
