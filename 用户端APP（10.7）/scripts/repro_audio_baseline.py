"""Reproduce the original relay frame mismatch without hardware or network."""
import json
from pathlib import Path
import struct
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from services.relay.app import app

session = str(uuid4())
config = {
    "schema_version": "1.0", "type": "audio.start", "session_id": session,
    "meeting_id": str(uuid4()), "device_id": "bench", "stream_id": "onsite_robot",
    "stream_key": 1, "direction": "uplink", "purpose": "onsite_voice",
    "command_id": None, "sample_rate_hz": 16000, "channels": 1,
    "encoding": "s16le", "frame_ms": 20,
}
frame = struct.pack("!4sBBHIIII", b"EFMA", 1, 0, 24, 1, 0, 0, 320) + bytes(640)
with TestClient(app) as client:
    with client.websocket_connect(f"/ws/audio/{session}?token=synthetic-invalid&device_id=bench") as ws:
        ws.send_json(config)
        ready = ws.receive_json()
        ws.send_bytes(frame)
        error = ws.receive_json()
        ws.send_json({"type": "audio.end", "session_id": session,
                      "stream_key": 1, "reason": "completed", "command_id": None})
assert ready["accepted"] is True
assert error["error_code"] == "INVALID_FRAME_SIZE" and error["received_bytes"] == 664
print(json.dumps({"result": "BLOCKERS_REPRODUCED", "invalid_token_accepted": True,
                  "contract_frame_bytes": len(frame), "relay_response": error}, indent=2))
