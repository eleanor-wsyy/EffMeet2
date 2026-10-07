"""Participant UI integration; keep the operator console and security unchanged."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from services.controller.app import create_app
from services.controller.contracts import ROOT
from services.controller.store import Store


class ParticipantTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="effmeet2-participant-")
        self.clock = [1000.0]
        self.app = create_app(Path(self.temp.name) / "test.sqlite3", clock=lambda: self.clock[0])
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.tokens = {p["actor"]: p["token"] for p in self.client.get("/api/demo/session").json()["profiles"]}
        self.mid = self.post("/api/v1/meetings", {"title": "用户端联调"}, expected=201)["meeting_id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def headers(self, actor="remote_1"):
        return {"Authorization": "Bearer " + self.tokens[actor]}

    def post(self, route, body, actor="operator", expected=200):
        response = self.client.post(route, json=body, headers=self.headers(actor))
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def snapshot(self, actor="remote_1"):
        response = self.client.get(f"/api/demo/meetings/{self.mid}/state", headers=self.headers(actor))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def utterance(self):
        u = {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "remote_1", "channel": "remote",
             "start_ms": 0, "end_ms": 1000, "text": "满溢检测用重量传感器。", "final": True, "revision": 1}
        self.post(f"/api/v1/meetings/{self.mid}/utterances", u, expected=201)
        return u

    def candidate(self):
        u = self.utterance()
        result = self.post(f"/api/v1/meetings/{self.mid}/analysis?mock_status=possibly_unresponded",
                           {"evidence_ids": [u["utterance_id"]]}, expected=202)
        return result["intervention"]

    def test_participant_mount_does_not_replace_console(self):
        response = self.client.get("/app/")
        self.assertEqual(response.status_code, 200)
        for screen in ["view-join", "view-live", "view-map"]:
            self.assertIn(f'id="{screen}"', response.text)
        expected = (ROOT / "services/controller/demo.html").read_text(encoding="utf-8")
        self.assertEqual(self.client.get("/").text, expected)
        self.assertEqual(self.client.get("/bench-camera.js").status_code, 200)
        self.assertEqual(self.client.get("/bench-audio.js").status_code, 200)

    def test_assets_and_modules_same_origin(self):
        for asset in ["styles.css", "state.js", "app.js", "manifest.json", "assets/link.svg", "assets/brand.svg", "assets/mic.svg"]:
            response = self.client.get("/app/" + asset)
            self.assertEqual(response.status_code, 200, asset)
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("img-src 'self' blob:", response.headers["content-security-policy"])

    def test_participant_does_not_weaken_auth_or_local_only(self):
        self.assertEqual(self.client.get(f"/api/demo/meetings/{self.mid}/state").status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/meetings/{self.mid}/viewpoint-map").status_code, 401)
        self.assertEqual(self.client.get("/app/", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/app/", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/app/../../.env").status_code, 404)

    def test_server_deadline_read_does_not_renew(self):
        self.candidate()
        first = self.snapshot()
        self.assertEqual(first["server_time"], 1000)
        self.assertEqual(first["interventions"][0]["expires_at"], 1120)
        self.clock[0] = 1110
        self.assertEqual(self.snapshot()["interventions"][0]["expires_at"], 1120)
        self.clock[0] = 1120
        expired = self.snapshot()
        self.assertEqual(expired["interventions"][0]["state"], "expired")
        self.assertEqual(expired["interventions"][0]["expires_at"], 1120)

    def test_map_revision_tracks_evidence_not_map_reads(self):
        initial = self.snapshot()["viewpoint_revision"]
        u = self.utterance()
        utterance_version = self.snapshot()["viewpoint_revision"]
        self.assertGreater(utterance_version, initial)
        self.client.get(f"/api/v1/meetings/{self.mid}/viewpoint-map", headers=self.headers())
        self.assertEqual(self.snapshot()["viewpoint_revision"], utterance_version)
        self.post(f"/api/v1/meetings/{self.mid}/analysis?mock_status=uncertain", {"evidence_ids": [u["utterance_id"]]}, expected=202)
        self.assertGreater(self.snapshot()["viewpoint_revision"], utterance_version)

    def test_owner_confirm_receipts_and_map(self):
        c = self.candidate()
        route = f"/api/v1/meetings/{self.mid}/interventions/{c['intervention_id']}/decision"
        body = {"decision": "confirm", "expected_revision": 1}
        self.post(route, body, "remote_2", 403)
        result = self.post(route, body, "remote_1", 202)
        self.assertEqual(result["receipts"][-1]["status"], "completed")
        self.assertEqual(self.snapshot()["interventions"][0]["state"], "completed")
        retry = self.post(route, body, "remote_1", 202)
        self.assertTrue(retry["replayed"])
        map_response = self.client.get(f"/api/v1/meetings/{self.mid}/viewpoint-map", headers=self.headers()).json()
        self.assertEqual(map_response["viewpoints"][0]["text"], "满溢检测用重量传感器。")
        # Robot playback is not an onsite response; the model status remains separate.
        self.assertEqual(map_response["viewpoints"][0]["response_status"], "possibly_unresponded")

    def test_outside_close_requires_no_decision_endpoint(self):
        self.candidate()
        before = self.snapshot()
        # Read-only reopening is what the scrim/close affordances leave behind.
        after = self.snapshot()
        self.assertEqual(after["interventions"], before["interventions"])
        self.assertEqual(after["commands"], [])

    def test_remote_reads_original_capture_with_auth(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        upload = self.client.post(f"/api/v1/meetings/{self.mid}/captures", files={"file": ("original.png", data, "image/png")}, headers=self.headers("operator"))
        self.assertEqual(upload.status_code, 201)
        cid = upload.json()["capture_id"]
        route = f"/api/v1/meetings/{self.mid}/captures/{cid}"
        self.assertEqual(self.client.get(route).status_code, 401)
        response = self.client.get(route, headers=self.headers())
        self.assertEqual(response.content, data)
        self.assertEqual(response.headers["content-type"], "image/png")

    def test_bench_snapshot_not_mislabelled_mock(self):
        store = Store(Path(self.temp.name) / "bench.sqlite3", clock=lambda: self.clock[0], bench=True)
        mid = store.create_meeting({"title": "台架"})["meeting_id"]
        self.assertEqual(store.snapshot(mid)["mode"], "bench")
        self.assertEqual(store.snapshot(mid)["server_time"], 1000)


    def recheck_route(self, candidate):
        return f"/api/v1/meetings/{self.mid}/interventions/{candidate['intervention_id']}/recheck"

    def test_expired_status_can_recheck_then_confirm_once(self):
        c = self.candidate()
        self.clock[0] = 1120
        route = self.recheck_route(c)
        renewed = self.post(route, {"expected_revision": 1}, "remote_1")
        self.assertEqual(renewed["state_revision"], 2)
        self.assertEqual(renewed["expires_at"], 1240)
        self.assertEqual(self.snapshot()["commands"], [])
        self.post(route, {"expected_revision": 1}, "remote_1", 409)
        decision_route = route.replace("/recheck", "/decision")
        self.post(decision_route, {"decision": "confirm", "expected_revision": 1}, "remote_1", 409)
        result = self.post(decision_route, {"decision": "confirm", "expected_revision": 2}, "remote_1", 202)
        self.assertEqual(result["receipts"][-1]["status"], "completed")
        replay = self.post(decision_route, {"decision": "confirm", "expected_revision": 2}, "remote_1", 202)
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(self.snapshot()["commands"]), 1)
        self.post(route, {"expected_revision": 3}, "remote_1", 409)

    def test_recheck_active_never_extends_deadline(self):
        c = self.candidate()
        self.clock[0] = 1100
        renewed = self.post(self.recheck_route(c), {"expected_revision": 1}, "remote_1")
        self.assertEqual(renewed["expires_at"], 1120)
        self.assertEqual(renewed["state_revision"], 1)
        self.assertEqual(self.snapshot()["commands"], [])

    def test_recheck_requires_owner_and_auth(self):
        c = self.candidate()
        self.clock[0] = 1121
        route = self.recheck_route(c)
        self.assertEqual(self.client.post(route, json={"expected_revision": 1}).status_code, 401)
        self.post(route, {"expected_revision": 1}, "remote_2", 403)
        self.post(route, {"expected_revision": 1}, "operator", 403)
        self.assertEqual(self.snapshot()["interventions"][0]["expires_at"], 1120)

    def test_recheck_rejects_changed_context_without_command(self):
        c = self.candidate()
        self.utterance()
        self.clock[0] = 1121
        result = self.post(self.recheck_route(c), {"expected_revision": 1}, "remote_1", 409)
        self.assertEqual(result["error"]["code"], "CONTEXT_CHANGED")
        self.assertEqual(self.snapshot()["commands"], [])
        self.assertEqual(self.snapshot()["interventions"][0]["state_revision"], 1)

    def test_recheck_does_not_override_dismissal(self):
        c = self.candidate()
        route = self.recheck_route(c)
        self.post(route.replace("/recheck", "/decision"), {"decision": "dismiss", "expected_revision": 1}, "remote_1", 202)
        self.clock[0] = 1200
        self.post(route, {"expected_revision": 2}, "remote_1", 409)
        self.assertEqual(self.snapshot()["interventions"][0]["state"], "dismissed")
        self.assertEqual(self.snapshot()["commands"], [])

    def test_recheck_rejects_verified_response(self):
        c = self.candidate()
        u = {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "onsite_1", "channel": "onsite",
             "start_ms": 1000, "end_ms": 2000, "text": "同意重量传感器方案。", "final": True, "revision": 1}
        self.post(f"/api/v1/meetings/{self.mid}/utterances", u, expected=201)
        self.app.state.store.verify_response(self.mid, c["claim_id"], {"response_utterance_ids": [u["utterance_id"]]}, "remote_1")
        self.clock[0] = 1121
        result = self.post(self.recheck_route(c), {"expected_revision": 1}, "remote_1", 409)
        self.assertEqual(result["error"]["code"], "ALREADY_RESPONDED")
        self.assertEqual(self.snapshot()["commands"], [])

    def test_recheck_cannot_inject_deadline_or_decision(self):
        c = self.candidate()
        route = self.recheck_route(c)
        for body in [{}, {"expected_revision": True}, {"expected_revision": 0},
                     {"expected_revision": 1, "expires_at": 9999}, {"expected_revision": 1, "decision": "confirm"}]:
            self.post(route, body, "remote_1", 422)
        self.assertEqual(self.snapshot()["commands"], [])


if __name__ == "__main__":
    unittest.main()
