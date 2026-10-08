"""Run the Figma-derived participant app through the existing controller (local-only)."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import uvicorn
from services.controller.app import create_app


def port_number(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be 1..65535")
    return port


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port_number, default=8765)
    parser.add_argument("--db", type=Path, help="Optional isolated database path")
    args = parser.parse_args()
    print(f"Participant app: http://127.0.0.1:{args.port}/app/")
    print("Existing operator console remains at /. Local demo identities are not production login.")
    uvicorn.run(create_app(db_path=args.db), host="127.0.0.1", port=args.port, workers=1)
