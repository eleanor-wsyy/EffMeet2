"""Real TCP/HTTP/WebSocket integration, synthetic providers, no sound/hardware."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from websockets.sync.client import connect


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="effmeet-network-") as tmp:
        log_path = Path(tmp) / "server.log"
        env = {**os.environ, "EFFMEET_DB_PATH": str(Path(tmp) / "bench.sqlite3"),
               "EFFMEET_FIXTURE_PORT": str(port), "PYTHONIOENCODING": "utf-8"}
        # A fixture must never accidentally call a real configured account.
        env.pop("QWEN_API_KEY", None)
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable, "-m", "tests.network_fixture"], cwd=ROOT,
                env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                with httpx.Client(base_url=base, trust_env=False, timeout=5) as http:
                    for _ in range(100):
                        try:
                            if http.get("/healthz").is_success:
                                break
                        except httpx.RequestError:
                            pass
                        if proc.poll() is not None:
                            raise RuntimeError("Fixture failed to start")
                        time.sleep(.1)
                    profiles = http.get("/api/demo/session").json()["profiles"]
                    tokens = {p["actor"]: p["token"] for p in profiles}
                    def request(method, path, body=None, actor="operator"):
                        r = http.request(method, path, json=body, headers={"Authorization": "Bearer " + tokens[actor]})
                        r.raise_for_status()
                        return r.json()
                    mid = request("POST", "/api/v1/meetings", {"title": "Synthetic TCP verification"})["meeting_id"]
                    wav_path = Path(tmp) / "input.wav"
                    with wave.open(str(wav_path), "wb") as wav:
                        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                        wav.writeframes(bytes(3200))
                    def client(*args):
                        r = subprocess.run([sys.executable, "scripts/bench_audio.py", "--url", base,
                            "--meeting", mid, *args], cwd=ROOT, env=env, capture_output=True, timeout=15)
                        if r.returncode:
                            raise RuntimeError(r.stderr.decode("utf-8", errors="replace"))
                    client("upload", str(wav_path), "--channel", "remote", "--speaker", "remote_1")
                    state = request("GET", f"/api/demo/meetings/{mid}/state")
                    assert state["utterances"][0]["text"].startswith("合成测试")
                    job = request("POST", f"/api/v1/meetings/{mid}/analysis",
                        {"evidence_ids": [state["utterances"][0]["utterance_id"]]})
                    for _ in range(100):
                        result = request("GET", f"/api/bench/meetings/{mid}/jobs/{job['job_id']}")
                        if result["status"] == "completed":
                            break
                        assert result["status"] != "failed", result
                        time.sleep(.02)
                    candidate = result["result"]["intervention"]
                    assert not request("GET", f"/api/demo/meetings/{mid}/state")["commands"]
                    path = f"/api/v1/meetings/{mid}/interventions/{candidate['intervention_id']}/decision"
                    body = {"decision": "confirm", "expected_revision": 1}
                    decision = request("POST", path, body, "remote_1")
                    cid = decision["command"]["command_id"]
                    client("play", cid, "--simulate", "--safe-pause")
                    state = request("GET", f"/api/demo/meetings/{mid}/state")
                    assert [r["status"] for r in state["commands"][0]["receipts"]] == ["accepted", "started", "completed"]
                    assert request("POST", path, body, "remote_1")["replayed"]
                    events = request("GET", f"/api/v1/meetings/{mid}/events")
                    assert next(e for e in events if e["event_type"] == "utterance.final")["mode"] == "mock"
                    assert all(e["mode"] == "mock" for e in events if e["event_type"] == "robot.receipt")
                    with connect(base.replace("http:", "ws:") + f"/api/v1/meetings/{mid}/events", proxy=None) as ws:
                        ws.send(json.dumps({"token": tokens["remote_1"], "after_seq": events[-2]["seq"]}))
                        assert json.loads(ws.recv(timeout=2))["seq"] == events[-1]["seq"]
                    print(json.dumps({"status": "PASS", "transport": "real HTTP + WebSocket",
                        "providers": "synthetic ASR/model/TTS and simulated audio sink",
                        "checks": ["WAV to EFMA", "FunASR wire handshake", "final transcript ledger",
                            "async model job", "owner confirmation", "PCM downlink with bounded ACK",
                            "drained receipt", "retry idempotency", "event resume"],
                        "hardware_verified": False}, indent=2))
            except Exception:
                print(log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
                raise
            finally:
                try:
                    with httpx.Client(trust_env=False, timeout=2) as shutdown:
                        shutdown.post(base + "/fixture/shutdown")
                    proc.wait(timeout=5)
                except (subprocess.TimeoutExpired, httpx.RequestError):
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
                    else:
                        proc.kill()
                    proc.wait()


if __name__ == "__main__":
    main()
