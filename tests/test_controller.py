"""No network, hardware, AI service or pytest dependency needed."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from services.controller.app import create_app
from services.controller.contracts import BUNDLE, ROOT, DemoError, validate
from services.controller.fakes import FakeRobot


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="effmeet2-tests-")
        self.path = Path(self.temp.name) / "test.sqlite3"
        self.time = [1000.0]
        self.robot = FakeRobot()
        self.app = create_app(self.path, robot=self.robot, clock=lambda: self.time[0])
        self.client = TestClient(self.app)
        self.client.__enter__()
        session = self.client.get("/api/demo/session").json()
        self.tokens = {x["actor"]: x["token"] for x in session["profiles"]}
        self.mid = self.post("/api/v1/meetings", {"title": "独立测试会议"}, expected=201)["meeting_id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def headers(self, actor):
        return {"Authorization": "Bearer " + self.tokens[actor]}

    def post(self, path, body, actor="operator", expected=200):
        response = self.client.post(path, json=body, headers=self.headers(actor))
        self.assertEqual(response.status_code, expected, response.text)
        result = response.json()
        if expected >= 400:
            validate("ErrorResponse", result)
        return result

    def events(self):
        response = self.client.get(f"/api/v1/meetings/{self.mid}/events", headers=self.headers("operator"))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def utterance(self, channel="remote", speaker="remote_1", text="先验证草图可读性。"):
        return {"utterance_id": str(uuid4()), "stream_id": "fixture", "speaker_id": speaker,
                "channel": channel, "start_ms": 100, "end_ms": 1000,
                "text": text, "final": True, "revision": 1}

    def add(self, body=None):
        body = body or self.utterance()
        self.post(f"/api/v1/meetings/{self.mid}/utterances", body, expected=201)
        return body

    def analyze(self, evidence, status="possibly_unresponded", expected=202):
        return self.post(f"/api/v1/meetings/{self.mid}/analysis?mock_status={status}",
                         {"evidence_ids": [x["utterance_id"] for x in evidence]}, expected=expected)

    def candidate(self):
        return self.analyze([self.add()])["intervention"]

    def decide(self, candidate, decision="confirm", actor="remote_1", revision=1, expected=202):
        return self.post(f"/api/v1/meetings/{self.mid}/interventions/{candidate['intervention_id']}/decision",
                         {"decision": decision, "expected_revision": revision}, actor=actor, expected=expected)

    def test_no_confirmation_no_command(self):
        self.candidate()
        self.assertEqual(self.robot.calls, [])
        self.assertFalse(any(e["event_type"] == "robot.command" for e in self.events()))

    def test_dismiss_has_no_command(self):
        result = self.decide(self.candidate(), "dismiss")
        self.assertIsNone(result["command"])
        self.assertEqual(self.robot.calls, [])

    def test_confirm_mock_receipts_and_schema(self):
        result = self.decide(self.candidate())
        self.assertEqual([x["status"] for x in result["receipts"]], ["accepted", "started", "completed"])
        self.assertEqual(len(self.robot.calls), 1)
        for event in self.events():
            validate("EventEnvelope", event)
            self.assertEqual(event["mode"], "mock")

    def test_same_decision_retry_is_idempotent(self):
        candidate = self.candidate()
        first = self.decide(candidate)
        count = len(self.events())
        retry = self.decide(candidate)
        self.assertTrue(retry["replayed"])
        self.assertEqual(first["command"], retry["command"])
        self.assertEqual(len(self.events()), count)
        self.assertEqual(len(self.robot.calls), 1)

    def test_concurrent_confirm_dispatches_once(self):
        candidate = self.candidate()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.app.state.store.decide(
                self.mid, candidate["intervention_id"], {"decision": "confirm", "expected_revision": 1}, "remote_1"
            ), range(4)))
        self.assertEqual(len({x["command"]["command_id"] for x in results}), 1)
        self.assertEqual(len(self.robot.calls), 1)

    def test_other_person_cannot_confirm(self):
        result = self.decide(self.candidate(), actor="remote_2", expected=403)
        self.assertEqual(result["error"]["code"], "NOT_OWNER")
        self.assertEqual(self.robot.calls, [])

    def test_body_cannot_inject_actor(self):
        candidate = self.candidate()
        self.post(f"/api/v1/meetings/{self.mid}/interventions/{candidate['intervention_id']}/decision",
                  {"decision": "confirm", "expected_revision": 1, "actor_speaker_id": "remote_1"},
                  actor="remote_2", expected=422)
        self.assertEqual(self.robot.calls, [])

    def test_direct_robot_command_endpoint_not_exposed(self):
        result = self.post("/api/v1/robot/commands", {}, expected=404)
        self.assertIn("error", result)
        self.assertEqual(self.robot.calls, [])

    def test_wrong_revision_cannot_execute(self):
        self.decide(self.candidate(), revision=4, expected=409)
        self.assertEqual(self.robot.calls, [])

    def test_expired_candidate_cannot_execute(self):
        candidate = self.candidate()
        self.time[0] += 121
        result = self.decide(candidate, expected=409)
        self.assertEqual(result["error"]["code"], "CANDIDATE_EXPIRED")
        self.assertEqual(self.robot.calls, [])

    def test_expired_analysis_renews_with_new_revision(self):
        utterance = self.add()
        first = self.analyze([utterance])["intervention"]
        self.time[0] += 121
        renewed = self.analyze([utterance])["intervention"]
        self.assertEqual(first["intervention_id"], renewed["intervention_id"])
        self.assertEqual(renewed["state_revision"], 2)
        self.decide(first, expected=409)
        self.decide(renewed, revision=2)
        self.assertEqual(len(self.robot.calls), 1)
        self.time[0] += 121
        after_done = self.analyze([utterance])
        self.assertTrue(after_done["replayed"])
        self.assertEqual(len(self.robot.calls), 1)

    def test_new_context_requires_reanalysis(self):
        candidate = self.candidate()
        self.add(self.utterance(channel="onsite", speaker="onsite_1", text="我回应一下。"))
        result = self.decide(candidate, expected=409)
        self.assertEqual(result["error"]["code"], "CONTEXT_CHANGED")
        self.assertEqual(self.robot.calls, [])

    def test_changed_decision_is_conflict(self):
        candidate = self.candidate()
        self.decide(candidate)
        self.decide(candidate, "dismiss", expected=409)
        self.assertEqual(len(self.robot.calls), 1)

    def test_responded_creates_no_candidate(self):
        remote = self.add()
        onsite = self.add(self.utterance(channel="onsite", speaker="onsite_1", text="同意先共享草图。"))
        result = self.analyze([remote, onsite], "responded")
        self.assertIsNone(result["intervention"])
        self.assertEqual(result["analysis"]["response_utterance_ids"], [onsite["utterance_id"]])
        self.assertEqual(self.robot.calls, [])

    def test_uncertain_creates_no_candidate(self):
        result = self.analyze([self.add()], "uncertain")
        self.assertIsNone(result["intervention"])
        self.assertEqual(self.robot.calls, [])

    def test_unknown_owner_abstains(self):
        result = self.analyze([self.add(self.utterance(speaker=None))], expected=422)
        self.assertEqual(result["error"]["code"], "OWNER_UNCLEAR")
        self.assertEqual(self.robot.calls, [])

    def test_same_analysis_retry_keeps_candidate(self):
        utterance = self.add()
        first = self.analyze([utterance])
        count = len(self.events())
        second = self.analyze([utterance])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["intervention"], second["intervention"])
        self.assertEqual(len(self.events()), count)
        self.analyze([utterance], "uncertain", expected=409)

    def test_same_utterance_retry_and_content_conflict(self):
        utterance = self.add()
        count = len(self.events())
        retry = self.post(f"/api/v1/meetings/{self.mid}/utterances", utterance)
        self.assertTrue(retry["replayed"])
        self.assertEqual(len(self.events()), count)
        changed = {**utterance, "text": "另一个观点"}
        self.post(f"/api/v1/meetings/{self.mid}/utterances", changed, expected=409)

    def test_partial_invalid_interval_and_blank_text_rejected(self):
        for overrides in [{"final": False}, {"start_ms": 2000}, {"text": "   "}]:
            self.post(f"/api/v1/meetings/{self.mid}/utterances", {**self.utterance(), **overrides}, expected=422)
        self.assertEqual(len(self.events()), 1)

    def test_cross_meeting_evidence_rejected(self):
        utterance = self.add()
        other = self.post("/api/v1/meetings", {"title": "另一会议"}, expected=201)["meeting_id"]
        self.post(f"/api/v1/meetings/{other}/analysis", {"evidence_ids": [utterance["utterance_id"]]}, expected=422)

    def test_remote_identity_cannot_submit_others_utterance(self):
        self.post(f"/api/v1/meetings/{self.mid}/utterances", self.utterance(speaker="remote_2"), actor="remote_1", expected=403)

    def test_summary_contains_verbatim_evidence_only(self):
        utterance = self.add()
        self.decide(self.analyze([utterance])["intervention"])
        summary = self.post(f"/api/v1/meetings/{self.mid}/summary", {}, expected=202)
        validate("Summary", summary)
        self.assertEqual(summary["items"][0]["text"], utterance["text"])
        self.assertEqual(summary["items"][0]["evidence_ids"], [utterance["utterance_id"]])
        self.assertTrue(all(x["kind"] != "decision" and x["verification_status"] == "unresolved" for x in summary["items"]))
        count = len(self.events())
        self.assertEqual(summary, self.post(f"/api/v1/meetings/{self.mid}/summary", {}, expected=202))
        self.assertEqual(len(self.events()), count)

    def test_event_seq_and_resume(self):
        self.decide(self.candidate())
        events = self.events()
        self.assertEqual([e["seq"] for e in events], list(range(1, len(events)+1)))
        resumed = self.client.get(f"/api/v1/meetings/{self.mid}/events?after_seq=3", headers=self.headers("operator")).json()
        self.assertEqual(resumed, events[3:])
        known = {x["event_id"] for x in events}
        self.assertTrue(all(e["parent_event_id"] is None or e["parent_event_id"] in known for e in events))

    def test_restart_recovers_without_replay(self):
        candidate = self.candidate()
        first = self.decide(candidate)
        count = len(self.events())
        rebooted = create_app(self.path, clock=lambda: self.time[0])
        with TestClient(rebooted) as client:
            token = next(x["token"] for x in client.get("/api/demo/session").json()["profiles"] if x["actor"] == "remote_1")
            result = client.post(f"/api/v1/meetings/{self.mid}/interventions/{candidate['intervention_id']}/decision",
                                json={"decision": "confirm", "expected_revision": 1}, headers={"Authorization": "Bearer " + token})
            self.assertEqual(result.status_code, 202)
            self.assertEqual(result.json()["command"], first["command"])
            self.assertTrue(result.json()["replayed"])
            self.assertEqual(rebooted.state.robot.calls, [])
            self.assertEqual(len(rebooted.state.store.events(self.mid)), count)

    def test_mock_device_failure_is_visible(self):
        self.robot.fail = True
        result = self.decide(self.candidate())
        self.assertEqual(result["receipts"][-1]["status"], "failed")
        self.assertFalse(any(x["status"] == "completed" for x in result["receipts"]))
        self.assertEqual(self.app.state.store.snapshot(self.mid)["interventions"][0]["state"], "failed")

    def test_no_auth_cross_site_bad_host_rejected(self):
        self.assertEqual(self.client.post("/api/v1/meetings", json={"title": "No token"}).status_code, 401)
        self.assertEqual(self.client.get("/api/demo/session", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/", headers={"Host": "evil.example"}).status_code, 403)

    def test_empty_summary_request_cannot_inject_fields(self):
        self.post(f"/api/v1/meetings/{self.mid}/summary", {"decision": "invent"}, expected=422)

    def test_invalid_event_timestamp_is_rejected(self):
        event = self.events()[0]
        for field in ["occurred_at", "received_at"]:
            bad = {**event, field: "not-a-timestamp"}
            with self.assertRaises(DemoError):
                validate("EventEnvelope", bad)

    def test_console_copy_names_view_owner_and_onsite_recipient(self):
        page = self.client.get("/").text
        for text in ["线上观点可能尚未获现场回应", "请机器人向现场提示", "不用向现场提示这条观点",
                     "提示接收方：现场参与讨论的人", "观点本人决定是否提示现场"]:
            self.assertIn(text, page)
        self.assertNotIn("可能未回应 → 产生候选", page)
        self.assertNotIn("[['confirm','请提醒'],['dismiss','不必提醒']]", page)

    def test_report_and_runtime_contract_stay_equal(self):
        documented = json.loads((ROOT / "docs/product/EffMeet2_contract_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(BUNDLE, documented)
        # Parse embedded JSON using the standard library, avoiding a BeautifulSoup runtime dependency.
        html = (ROOT / "docs/product/EffMeet2_论文依据与技术路径.html").read_text(encoding="utf-8")
        import re
        match = re.search(r'<script[^>]*id="contract-bundle"[^>]*>(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), BUNDLE)
    def test_capture_upload_and_read(self):
        image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        response = self.client.post(
            f"/api/v1/meetings/{self.mid}/captures",
            files={"file": ("sketch.png", image_data, "image/png")},
            headers=self.headers("operator"),
        )
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertIn("capture_id", result)
        self.assertEqual(result["event"]["event_type"], "capture.created")
        # list captures
        listed = self.client.get(
            f"/api/v1/meetings/{self.mid}/captures",
            headers=self.headers("operator"),
        ).json()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["filename"], "sketch.png")
        # read image bytes
        img = self.client.get(
            f"/api/v1/meetings/{self.mid}/captures/{result['capture_id']}",
            headers=self.headers("operator"),
        )
        self.assertEqual(img.status_code, 200)
        self.assertEqual(img.content, image_data)
        self.assertEqual(img.headers["content-type"], "image/png")

    def test_capture_remote_can_read(self):
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 50
        r = self.client.post(
            f"/api/v1/meetings/{self.mid}/captures",
            files={"file": ("whiteboard.jpg", image_data, "image/jpeg")},
            headers=self.headers("operator"),
        )
        self.assertEqual(r.status_code, 201)
        cid = r.json()["capture_id"]
        # remote identity can list and read
        listed = self.client.get(
            f"/api/v1/meetings/{self.mid}/captures",
            headers=self.headers("remote_1"),
        ).json()
        self.assertEqual(len(listed), 1)
        img = self.client.get(
            f"/api/v1/meetings/{self.mid}/captures/{cid}",
            headers=self.headers("remote_1"),
        )
        self.assertEqual(img.status_code, 200)

    def test_capture_non_image_rejected(self):
        r = self.client.post(
            f"/api/v1/meetings/{self.mid}/captures",
            files={"file": ("evil.txt", b"not an image", "text/plain")},
            headers=self.headers("operator"),
        )
        self.assertEqual(r.status_code, 422)
        validate("ErrorResponse", r.json())

    def test_capture_no_auth_rejected(self):
        r = self.client.post(
            f"/api/v1/meetings/{self.mid}/captures",
            files={"file": ("sketch.png", b"\x89PNG", "image/png")},
        )
        self.assertEqual(r.status_code, 401)

    def test_capture_not_found(self):
        r = self.client.get(
            f"/api/v1/meetings/{self.mid}/captures/{uuid4()}",
            headers=self.headers("operator"),
        )
        self.assertEqual(r.status_code, 404)
        validate("ErrorResponse", r.json())

    def test_viewpoint_map_build(self):
        self.add(self.utterance(channel="remote", speaker="remote_1", text="我们先用A方案。"))
        self.add(self.utterance(channel="onsite", speaker="onsite_1", text="同意，先验证可行性。"))
        r = self.client.post(
            f"/api/v1/meetings/{self.mid}/viewpoint-map",
            json={},
            headers=self.headers("operator"),
        )
        self.assertEqual(r.status_code, 202, r.text)
        vmap = r.json()
        validate("ViewpointMap", vmap)
        self.assertEqual(len(vmap["viewpoints"]), 2)
        for vp in vmap["viewpoints"]:
            self.assertEqual(vp["response_status"], "no_analysis")

    def test_viewpoint_map_with_analysis(self):
        u1 = self.add(self.utterance(channel="remote", speaker="remote_1"))
        self.add(self.utterance(channel="onsite", speaker="onsite_1", text="我回应一下。"))
        self.analyze([u1], status="possibly_unresponded")
        r = self.client.post(
            f"/api/v1/meetings/{self.mid}/viewpoint-map",
            json={},
            headers=self.headers("operator"),
        )
        self.assertEqual(r.status_code, 202)
        vmap = r.json()
        validate("ViewpointMap", vmap)
        analyzed = [vp for vp in vmap["viewpoints"] if vp["response_status"] != "no_analysis"]
        self.assertEqual(len(analyzed), 1)
        self.assertEqual(analyzed[0]["response_status"], "possibly_unresponded")


if __name__ == "__main__":
    unittest.main()
