"""Create synthetic participant QA data through the existing localhost mock API."""
import argparse
from uuid import uuid4
import httpx


# Artificial demo evidence, not UI copy, meeting recordings, or model output.
DEMO_TEXTS = (
    "满溢检测可以先采用重量传感器，便于验证方案。",
    "折叠箱体的连接处可以先做承重测试，再决定是否采用卡扣。",
    "投放口可以增加可拆卸挡板，方便后续清洁和维护。",
    "分类提示可以先用图形标识，降低第一次投放时的理解成本。",
)


def seed_demo(client, count=4):
    """Create independent owned candidates at one shared evidence revision.

    Store *all* evidence before analysis. Interleaving evidence and analysis
    would stale earlier candidates when the next utterance advances context.
    This helper deliberately keeps the server's 120s deadline and auth gates.
    """
    if type(count) is not int or not 1 <= count <= len(DEMO_TEXTS):
        raise ValueError(f"candidates must be 1..{len(DEMO_TEXTS)}")
    health = client.get("/healthz")
    health.raise_for_status()
    if health.json()["mode"] != "mock":
        raise ValueError("Synthetic seed is mock-only; no hardware or real-model execution.")
    session = client.get("/api/demo/session")
    session.raise_for_status()
    profiles = session.json()["profiles"]
    headers = {"Authorization": "Bearer " + next(p["token"] for p in profiles if p["actor"] == "operator")}
    response = client.post("/api/v1/meetings", json={"title": "产品讨论 · 用户端联调"}, headers=headers)
    response.raise_for_status()
    mid = response.json()["meeting_id"]
    evidence = []
    for index, text in enumerate(DEMO_TEXTS[:count]):
        utterance = {"utterance_id": str(uuid4()), "stream_id": "manual", "speaker_id": "remote_1",
                     "channel": "remote", "start_ms": index * 2000, "end_ms": index * 2000 + 1000,
                     "text": text, "final": True, "revision": 1}
        response = client.post(f"/api/v1/meetings/{mid}/utterances", json=utterance, headers=headers)
        response.raise_for_status()
        evidence.append(utterance["utterance_id"])
    for uid in evidence:
        response = client.post(f"/api/v1/meetings/{mid}/analysis?mock_status=possibly_unresponded",
                               json={"evidence_ids": [uid]}, headers=headers)
        response.raise_for_status()
    return mid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--candidates", type=int, choices=range(1, len(DEMO_TEXTS) + 1), default=4)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    base = f"http://127.0.0.1:{args.port}"
    with httpx.Client(base_url=base, timeout=15) as client:
        try:
            mid = seed_demo(client, args.candidates)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Participant invite: {base}/app/?meeting_id={mid}")
        print(f"Meeting ID: {mid}")
        print(f"Synthetic candidates: {args.candidates}; each has separate evidence and decision state.")
        print("Use local test identity remote_1. Candidates expire 120s after creation; reopening does not renew them.")
