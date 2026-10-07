"""Compatibility entrypoint for the unified bench; one process per database."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    print("EffMeet 2 unified bench (compatibility port): http://127.0.0.1:8766")
    print("Media: /device/v1/audio and /device/v1/playback; paired Authorization header required.")
    print("Prefer scripts/run_bench.py. Do not start another process against this database.")
    uvicorn.run("services.relay.app:app", host="127.0.0.1", port=8766, workers=1)
