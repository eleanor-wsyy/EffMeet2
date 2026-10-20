"""Re-pair the robot and provision it over serial (media_token has a 1 h TTL).

Creates a fresh pair token on the bench controller and writes Wi-Fi/controller/
meeting/token into the board's NVS over the UART REPL, then the board reboots.

  .venv/Scripts/python.exe scripts/reprovision_board.py --meeting <meeting_id> \
      [--port COM3] [--ssid EffMeet-Link] [--pass effmeet88] \
      [--controller http://192.168.137.1:8799] [--device robot_a] \
      [--upstream http://127.0.0.1:8768]

The operator token is taken from the bench's /api/demo/session (localhost demo
identity, not a real account). Wi-Fi credentials and the media token go only to
the device NVS; they are never printed or written to the repo.
"""
import argparse
import json
import sys
import time
import urllib.request

def call(method, path, token=None, body=None, base="http://127.0.0.1:8768"):
    req = urllib.request.Request(base + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json",
                 **({"Authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--meeting", required=True, help="meeting_id the device joins")
    p.add_argument("--device", default="robot_a")
    p.add_argument("--port", default="COM3")
    p.add_argument("--ssid", default="EffMeet-Link")
    p.add_argument("--pass", dest="wifi_pass", default="effmeet88")
    p.add_argument("--controller", default="http://192.168.137.1:8799")
    p.add_argument("--upstream", default="http://127.0.0.1:8768")
    args = p.parse_args()

    profiles = call("GET", "/api/demo/session", base=args.upstream)["profiles"]
    op = next(x["token"] for x in profiles if x["actor"] == "operator")
    pair = call("POST",
                f"/api/v1/meetings/{args.meeting}/devices/{args.device}/pair",
                op, None, base=args.upstream)
    token = pair["media_token"]
    print(f"paired {args.device} at {pair['paired_at']} (token hidden)")

    import serial
    cmd = (f"provision {args.ssid} {args.wifi_pass} {args.controller} "
           f"{args.meeting} {token}")
    ser = serial.Serial(args.port, 115200, timeout=0.1)
    ser.setDTR(False)
    ser.setRTS(False)
    time.sleep(0.3)
    ser.read(ser.in_waiting or 1)
    ser.write(cmd.encode() + b"\r\n")
    out = b""
    end = time.time() + 5
    while time.time() < end:
        n = ser.in_waiting
        if n:
            out += ser.read(n)
            if b"provisioned" in out:
                break
        else:
            time.sleep(0.05)
    ser.close()
    if b"provisioned" in out:
        print("board provisioned; rebooting and rejoining")
        return 0
    print("board did not acknowledge provisioning; is the REPL up?")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
