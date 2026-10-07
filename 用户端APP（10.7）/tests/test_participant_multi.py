"""Multi-candidate mock demonstrations use real controller validation."""
import unittest
from unittest.mock import Mock
import test_participant as participant_test
from scripts.seed_participant_demo import seed_demo


class MultiCandidateTests(unittest.TestCase):
    setUp = participant_test.ParticipantTests.setUp
    tearDown = participant_test.ParticipantTests.tearDown
    headers = participant_test.ParticipantTests.headers
    post = participant_test.ParticipantTests.post
    snapshot = participant_test.ParticipantTests.snapshot
    recheck_route = participant_test.ParticipantTests.recheck_route
    def test_demo_independent_decisions(self):
        self.mid = seed_demo(self.client)
        rows = self.snapshot()["interventions"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({c["candidate"]["intervention_id"] for c in rows}), 4)
        self.assertEqual(len({c["candidate"]["claim_id"] for c in rows}), 4)
        self.assertTrue(all(c["state"] == "awaiting_confirmation" for c in rows))
        for c in rows[:2]:
            route = f"/api/v1/meetings/{self.mid}/interventions/{c['candidate']['intervention_id']}/decision"
            body = {"decision": "confirm", "expected_revision": c["state_revision"]}
            self.post(route, body, "remote_2", 403)
            result = self.post(route, body, "remote_1", 202)
            self.assertEqual(result["receipts"][-1]["status"], "completed")
            self.assertTrue(self.post(route, body, "remote_1", 202)["replayed"])
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot["commands"]), 2)
        states = {c["candidate"]["intervention_id"]: c["state"] for c in snapshot["interventions"]}
        self.assertTrue(all(states[c["candidate"]["intervention_id"]] == "awaiting_confirmation" for c in rows[2:]))

    def test_multiple_expired_recheck_remains_independent(self):
        self.mid = seed_demo(self.client)
        rows = self.snapshot()["interventions"]
        self.clock[0] = 1121
        self.assertTrue(all(c["state"] == "expired" for c in self.snapshot()["interventions"]))
        for c in rows[:2]:
            renewed = self.post(self.recheck_route(c["candidate"]), {"expected_revision": 1}, "remote_1")
            self.assertEqual(renewed["expires_at"], 1241)
            self.post(self.recheck_route(c["candidate"]).replace("/recheck", "/decision"),
                      {"decision": "confirm", "expected_revision": 2}, "remote_1", 202)
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot["commands"]), 2)
        remaining = {c["candidate"]["intervention_id"]: c for c in snapshot["interventions"]}
        for c in rows[2:]:
            self.assertEqual(remaining[c["candidate"]["intervention_id"]]["state"], "expired")
            self.assertEqual(remaining[c["candidate"]["intervention_id"]]["expires_at"], 1120)

    def test_seed_count_and_mock_guard(self):
        for value in [0, 5, True, "4"]:
            client = Mock()
            with self.assertRaises(ValueError):
                seed_demo(client, value)
            client.get.assert_not_called()
        client = Mock()
        client.get.return_value.json.return_value = {"mode": "bench"}
        with self.assertRaises(ValueError):
            seed_demo(client)
        client.post.assert_not_called()

    def test_single_candidate_option(self):
        self.mid = seed_demo(self.client, 1)
        self.assertEqual(len(self.snapshot()["interventions"]), 1)


if __name__ == "__main__":
    unittest.main()
