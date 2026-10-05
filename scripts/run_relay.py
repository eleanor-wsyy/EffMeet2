"""Run the media relay service; localhost only."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    print("EffMeet 2 media relay: http://127.0.0.1:8766")
    print("WebSocket endpoint: ws://127.0.0.1:8766/ws/audio/{session_id}")
    uvicorn.run("services.relay.app:app", host="127.0.0.1", port=8766, workers=1)
