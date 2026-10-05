"""Unified local bench. ASR and Qwen are opt-in; no silent mock fallback."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from services.controller.app import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    os.environ.setdefault("EFFMEET_DB_PATH", str(ROOT / "data/bench.sqlite3"))
    print(f"EffMeet bench: http://127.0.0.1:{args.port} (single process; localhost only)")
    uvicorn.run(create_app(bench=True), host="127.0.0.1", port=args.port, workers=1, ws_max_size=65536)
