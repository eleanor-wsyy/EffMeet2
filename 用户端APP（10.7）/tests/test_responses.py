"""Owner response verification using synthetic model output."""
import json
import unittest
from uuid import uuid4
from tests import test_bench as bench


class ResponseTests(unittest.TestCase):
    setUp = bench.BenchTests.setUp
    tearDown = bench.BenchTests.tearDown
    post = bench.BenchTests.post
    utterance = bench.BenchTests.utterance
    candidate = bench.BenchTests.candidate
    command = bench.BenchTests.command

    def onsite(self, text="同意，先检查草图。"):
        u = {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "onsite_1",
             "channel": "onsite", "start_ms": 0, "end_ms": 1000, "text": text,
             "final": True, "revision": 1}
        self.post(f"/api/v1/meetings/{self.mid}/utterances", u, 201)
        return u["utterance_id"]

    def verify(self, claim, ids, expected=200, actor="remote_1"):
        return self.post(f"/api/bench/meetings/{self.mid}/claims/{claim}/response-verification",
                         {"response_utterance_ids": ids}, expected, actor)

    def test_owner_evidence_and_idempotency(self):
        earlier = self.onsite()
        c = self.candidate()
        claim = c["claim_id"]
        rid = self.onsite()
        self.verify(claim, [rid], 403, "remote_2")
        self.verify(claim, [], 422)
        self.verify(claim, [earlier], 422)
        self.verify(claim, [c["evidence_ids"][0]], 422)
        self.verify(claim, [str(uuid4())], 422)
        first = self.verify(claim, [rid])
        second = self.verify(claim, [rid])
        self.assertEqual(first["event"], second["event"])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["event"]["mode"], "manual")
        self.verify(claim, [self.onsite("补充回复")], 409)
        result = self.post(f"/api/v1/meetings/{self.mid}/interventions/{c['intervention_id']}/decision",
                          {"decision": "confirm", "expected_revision": 1}, 409, "remote_1")
        self.assertEqual(result["error"]["code"], "ALREADY_RESPONDED")
        store = self.app.state.store
        request = {"evidence_ids": c["evidence_ids"]}
        self.assertIsNone(store.analyze(self.mid, request, "possibly_unresponded")["intervention"])
        self.assertIsNone(store.analyze(self.mid, request, "possibly_unresponded")["intervention"])

    def test_cross_meeting_and_summary(self):
        c = self.candidate()
        original = self.mid
        self.mid = self.post("/api/v1/meetings", {"title": "another"}, 201)["meeting_id"]
        foreign = self.onsite()
        self.verify(c["claim_id"], [foreign], 404)
        self.mid = original
        self.verify(c["claim_id"], [foreign], 422)
        rid = self.onsite()
        before = self.post(f"/api/v1/meetings/{self.mid}/summary", {}, 202)
        self.verify(c["claim_id"], [rid])
        after = self.post(f"/api/v1/meetings/{self.mid}/summary", {}, 202)
        self.assertNotEqual(before, after)
        self.assertIn('human_verified', json.dumps(after))
        tracking = self.app.state.store.response_tracking(self.mid)
        self.assertEqual(tracking["claims"][0]["verified_response_ids"], [rid])
        self.assertEqual(tracking["claims"][0]["verification_status"], "human_verified")

    def test_queued_reminder_cancelled(self):
        cid, _ = self.command()
        claim = self.app.state.store.response_tracking(self.mid)["claims"][0]["claim_id"]
        self.verify(claim, [self.onsite()])
        command = self.runtime.command(cid)
        self.assertEqual(command["state"], "failed")
        self.assertEqual(json.loads(command["receipts"])[-1]["error_code"], "RESPONSE_VERIFIED")
