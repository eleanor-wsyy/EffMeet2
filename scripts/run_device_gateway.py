"""Run the LAN device gateway against a loopback controller.

Only device routes are exposed. Use on an isolated demo network only.

  powershell:  .\.venv\Scripts\python.exe scripts\run_device_gateway.py
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn

from services.device_gateway import create_device_gateway


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", default="http://127.0.0.1:8768")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8799)
    args = parser.parse_args()
    parsed = urlparse(args.upstream)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("upstream must be a loopback controller")
    print(f"EffMeet device gateway: http://{args.host}:{args.port} -> {args.upstream}")
    print("Only /healthz, /device/v1/audio, /device/v1/playback and "
          "/api/v1/meetings/{id}/events are forwarded.")
    uvicorn.run(create_device_gateway(args.upstream), host=args.host, port=args.port, workers=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
