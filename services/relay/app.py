"""EffMeet 2 media relay service.

Receives PCM audio from devices (uplink) and forwards to the controller.
Sends TTS audio to devices (downlink). Runs as a separate process from
the controller to keep media I/O out of the business transaction path.

Usage:
    python -m services.relay.app
    # or
    uvicorn services.relay.app:app --host 127.0.0.1 --port 8766

The relay does NOT handle business logic. It only:
1. Accepts WebSocket connections from authenticated devices
2. Receives PCM frames (s16le, 16kHz, mono, 20ms per frame)
3. Forwards audio data to the controller via HTTP POST
4. Receives TTS audio from the controller and pushes to devices
"""
import json
import os
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI(title="EffMeet 2 · 媒体中继", version="0.1.0", docs_url=None, redoc_url=None)

CONTROLLER_URL = os.environ.get("EFFMEET_CONTROLLER_URL", "http://127.0.0.1:8765")

# Active WebSocket connections: {session_id: websocket}
active_sessions: dict[str, WebSocket] = {}


@app.get("/healthz")
def health():
    return {"ok": True, "service": "relay", "active_sessions": len(active_sessions)}


@app.websocket("/ws/audio/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str):
    """Handle a single audio stream session.

    Protocol:
    - Client connects with ?token=<media_token>&device_id=<device_id>
    - Client sends JSON config frame (AudioStreamConfig)
    - Server responds with JSON ready frame (AudioStreamReady)
    - Client sends binary PCM frames (640 bytes = 20ms at 16kHz s16le mono)
    - Client sends JSON end frame (AudioStreamEnd)
    - Server closes connection
    """
    token = websocket.query_params.get("token", "")
    device_id = websocket.query_params.get("device_id", "")
    if not token or not device_id:
        await websocket.close(code=4001, reason="Missing token or device_id")
        return

    # TODO: Verify token with controller before accepting
    # For now, accept all connections in mock mode
    await websocket.accept()
    active_sessions[session_id] = websocket

    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                data = json.loads(message["text"])
                msg_type = data.get("type")
                if msg_type == "audio.start":
                    # Validate config and respond with ready
                    ready = {
                        "type": "audio.ready",
                        "session_id": data["session_id"],
                        "stream_key": data["stream_key"],
                        "accepted": True,
                        "error_code": None,
                    }
                    await websocket.send_json(ready)
                elif msg_type == "audio.end":
                    # Clean up session
                    break
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
            elif message.get("bytes"):
                # PCM audio frame received
                # TODO: Forward to controller for ASR processing
                # For now, just acknowledge receipt
                frame_size = len(message["bytes"])
                # Expected: 640 bytes (20ms at 16kHz s16le mono)
                if frame_size != 640:
                    await websocket.send_json({
                        "type": "error",
                        "error_code": "INVALID_FRAME_SIZE",
                        "expected_bytes": 640,
                        "received_bytes": frame_size,
                    })
    except WebSocketDisconnect:
        pass
    finally:
        active_sessions.pop(session_id, None)


@app.post("/api/tts/{session_id}")
async def push_tts(session_id: str, audio: bytes = b""):
    """Receive TTS audio from controller and push to device via WebSocket."""
    ws = active_sessions.get(session_id)
    if ws is None:
        return JSONResponse({"error": "session not found"}, status_code=404)
    if audio:
        await ws.send_bytes(audio)
    return {"ok": True, "session_id": session_id}


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": list(active_sessions.keys())}
