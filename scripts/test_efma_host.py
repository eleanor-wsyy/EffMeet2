"""Compile and run the EFMA host test without ESP-IDF or a device.

Uses the optional `ziglang` wheel as the C compiler:

    ./.venv/Scripts/python.exe -m pip install ziglang
    ./.venv/Scripts/python.exe scripts/test_efma_host.py

The codec is pure C; this proves protocol.py parity on the host only. It does
not compile the ESP-IDF project or validate any device link.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "firmware/esp32/test"
MAIN_DIR = ROOT / "firmware/esp32/main"


def main() -> int:
    try:
        import ziglang  # noqa: F401
    except ImportError:
        print("ziglang is not installed; run: python -m pip install ziglang", file=sys.stderr)
        return 2
    output = Path(tempfile.gettempdir()) / "effmeet_efma_host_test.exe"
    compile_command = [
        sys.executable, "-m", "ziglang", "cc", "-std=c11", "-Wall", "-Wextra",
        "-I", str(MAIN_DIR), str(TEST_DIR / "test_efma_host.c"),
        str(MAIN_DIR / "efma_codec.c"), "-o", str(output),
    ]
    subprocess.run(compile_command, check=True)
    subprocess.run([str(output)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
