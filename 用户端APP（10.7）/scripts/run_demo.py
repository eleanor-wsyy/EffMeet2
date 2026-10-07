"""Run from any directory; localhost only, single worker, fake adapters only."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from services.controller.app import create_app

if __name__ == "__main__":
    print("EffMeet 2 mock demo: http://127.0.0.1:8765")
    print("No microphone, AI API, TTS audio, or robot hardware is used.")
    uvicorn.run(create_app(), host="127.0.0.1", port=8765, workers=1)
