"""Exercise an already running localhost demo through actual HTTP requests."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Only the local HTTP mock service is allowed.")
    fixture = json.loads((Path(__file__).resolve().parents[1] / "fixtures/demo/closed_loop.json").read_text(encoding="utf-8"))
    with httpx.Client(base_url=args.base_url, timeout=10, trust_env=False) as client:
        health = client.get("/healthz").json()
        assert health["mode"] == "mock" and health["hardware_connected"] is False
        session = client.get("/api/demo/session")
        session.raise_for_status()
        tokens = {x["actor"]: x["token"] for x in session.json()["profiles"]}

        def request(method, path, body=None, actor="operator", expected=200):
            result = client.request(method, path, json=body, headers={"Authorization": "Bearer " + tokens[actor]})
            assert result.status_code == expected, f"{path}: HTTP {result.status_code} {result.text}"
            return result.json()

        def meeting(title):
            return request("POST", "/api/v1/meetings", {"title": title}, expected=201)["meeting_id"]

        def add(mid, kind):
            value = {**fixture[kind], "utterance_id": str(uuid4())}
            request("POST", f"/api/v1/meetings/{mid}/utterances", value, expected=201)
            return value["utterance_id"]

        def analyze(mid, ids, scenario):
            return request("POST", f"/api/v1/meetings/{mid}/analysis?mock_status={scenario}", {"evidence_ids": ids}, expected=202)

        def state(mid):
            return request("GET", f"/api/demo/meetings/{mid}/state")

        mid = meeting("HTTP smoke · 本人确认及重复请求")
        uid = add(mid, "remote")
        candidate = analyze(mid, [uid], "possibly_unresponded")["intervention"]
        assert not state(mid)["commands"], "Unconfirmed candidate dispatched"
        decision_path = f"/api/v1/meetings/{mid}/interventions/{candidate['intervention_id']}/decision"
        payload = {"decision": "confirm", "expected_revision": 1}
        request("POST", decision_path, payload, actor="remote_2", expected=403)
        first = request("POST", decision_path, payload, actor="remote_1", expected=202)
        second = request("POST", decision_path, payload, actor="remote_1", expected=202)
        assert second["replayed"] and first["command"] == second["command"]
        assert len(state(mid)["commands"]) == 1
        assert first["receipts"][-1]["status"] == "completed"
        summary = request("POST", f"/api/v1/meetings/{mid}/summary", {}, expected=202)
        assert summary["items"][0]["evidence_ids"] == [uid]
        events = request("GET", f"/api/v1/meetings/{mid}/events")
        assert all(e["mode"] == "mock" for e in events)
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1))

        dismissed = meeting("HTTP smoke · 不必提醒")
        cid = analyze(dismissed, [add(dismissed, "remote")], "possibly_unresponded")["intervention"]["intervention_id"]
        request("POST", f"/api/v1/meetings/{dismissed}/interventions/{cid}/decision",
                {"decision": "dismiss", "expected_revision": 1}, actor="remote_1", expected=202)
        assert not state(dismissed)["commands"]

        for scenario in ["responded", "uncertain"]:
            test_mid = meeting("HTTP smoke · " + scenario)
            ids = [add(test_mid, "remote")]
            if scenario == "responded":
                ids.append(add(test_mid, "response"))
            result = analyze(test_mid, ids, scenario)
            assert result["intervention"] is None and not state(test_mid)["commands"]

        print(json.dumps({"status": "PASS", "mode": "mock", "hardware_connected": False,
                          "checks": ["等待确认不执行", "他人不能代确认", "确认一次", "重复请求不重复执行",
                                     "拒绝不执行", "已回应不介入", "不确定弃权", "会后原文回溯", "seq有序且mode=mock"],
                          "main_meeting_id": mid}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
