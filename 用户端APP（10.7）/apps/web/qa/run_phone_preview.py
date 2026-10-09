"""Start an ephemeral, password-gated synthetic meeting via a temporary HTTPS tunnel."""
import argparse
import ipaddress
from contextlib import ExitStack
import os
from pathlib import Path
from queue import Empty, Queue
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.seed_participant_demo import seed_demo

TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def wait_for(url, *, status=200, seconds=15, verify=True):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=2, follow_redirects=False, trust_env=False, verify=verify)
            if response.status_code == status:
                return
        except httpx.HTTPError:
            pass
        time.sleep(.2)
    raise RuntimeError(f"local service did not start: {url}")


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def tunnel_url(process, timeout=50):
    messages = Queue()

    def read_logs():
        for line in process.stdout:
            match = TUNNEL_URL.search(line)
            if match:
                messages.put(match.group())
            if "ERR" in line or "error" in line.lower():
                messages.put("log: " + line.strip()[:200])

    threading.Thread(target=read_logs, daemon=True).start()
    deadline = time.monotonic() + timeout
    errors = []
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("HTTPS tunnel exited before announcing its URL: " + "; ".join(errors[-3:]))
        try:
            line = messages.get(timeout=.5)
        except Empty:
            continue
        if line.startswith("https://"):
            return line
        errors.append(line)
    raise RuntimeError("HTTPS tunnel did not announce a URL: " + "; ".join(errors[-3:]))



def make_lan_cert(openssl, ip):
    """Keep a local, ignored short-term QA CA; never upload the private key."""
    folder = ROOT / ".local" / "phone-qa-cert"
    folder.mkdir(parents=True, exist_ok=True)
    ca_key, ca_crt = folder / "root.key", folder / "root.crt"
    def run(*args):
        subprocess.run([str(openssl), *map(str, args)], check=True, cwd=folder,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    valid = ca_key.is_file() and ca_crt.is_file() and subprocess.run(
        [str(openssl), "x509", "-checkend", "86400", "-noout", "-in", str(ca_crt)],
        capture_output=True).returncode == 0
    if not valid:
        run("req", "-x509", "-newkey", "rsa:3072", "-noenc", "-days", "30",
            "-keyout", ca_key, "-out", ca_crt, "-subj", "/CN=EffMeet2 Local Phone QA Root",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    leaf_key, leaf_csr, leaf_crt = folder / "server.key", folder / "server.csr", folder / "server.crt"
    extensions = folder / "server.ext"
    extensions.write_text("basicConstraints=critical,CA:FALSE\n"
                          "keyUsage=critical,digitalSignature,keyEncipherment\n"
                          "extendedKeyUsage=serverAuth\n"
                          f"subjectAltName=IP:{ip}\n", encoding="ascii")
    run("req", "-newkey", "rsa:2048", "-noenc", "-keyout", leaf_key,
        "-out", leaf_csr, "-subj", "/CN=EffMeet2 Phone QA")
    run("x509", "-req", "-in", leaf_csr, "-CA", ca_crt, "-CAkey", ca_key,
        "-CAcreateserial", "-out", leaf_crt, "-days", "7", "-extfile", extensions)
    run("verify", "-CAfile", ca_crt, leaf_crt)
    shutil.copyfile(ca_crt, folder / "effmeet2-qa-root.cer")
    return ca_crt, leaf_crt, leaf_key

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloudflared", type=Path, help="Official cloudflared executable")
    parser.add_argument("--local-check-only", action="store_true", help="Test gateway without opening an HTTPS tunnel")
    parser.add_argument("--lan-ip", help="Private IPv4 address on same phone hotspot/Wi-Fi (local HTTPS)")
    parser.add_argument("--openssl", type=Path, help="OpenSSL binary for a temporary LAN certificate")
    parser.add_argument("--controller-port", type=int, default=8878)
    parser.add_argument("--gateway-port", type=int, default=8877)
    args = parser.parse_args()
    if args.controller_port == args.gateway_port or any(not 1024 <= p <= 65535 for p in (args.controller_port, args.gateway_port)):
        parser.error("use two different unprivileged ports")
    if args.lan_ip:
        ip = ipaddress.IPv4Address(args.lan_ip)
        if not ip.is_private or ip.is_loopback or ip.is_link_local:
            parser.error("--lan-ip must be a private LAN IPv4 address")
    if args.local_check_only and args.lan_ip:
        parser.error("choose either --local-check-only or --lan-ip")
    default_binary = ROOT / ".local" / "tools" / "cloudflared.exe"
    binary = args.cloudflared or Path(shutil.which("cloudflared") or default_binary)
    if not args.local_check_only and not args.lan_ip and not binary.is_file():
        parser.error("cloudflared missing; put official cloudflared.exe in .local/tools or pass --cloudflared PATH")
    code = secrets.token_urlsafe(24)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    (ROOT / ".local").mkdir(exist_ok=True)
    controller = gateway = tunnel = None
    with ExitStack() as stack:
        sandbox = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="effmeet2-phone-", dir=ROOT / ".local")))
        log = stack.enter_context((sandbox / "controller.log").open("w", encoding="utf-8"))
        try:
            controller = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "run_participant.py"),
                                           "--port", str(args.controller_port), "--db", str(sandbox / "demo.sqlite3")],
                                          cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            upstream = f"http://127.0.0.1:{args.controller_port}"
            wait_for(upstream + "/healthz")
            with httpx.Client(base_url=upstream, timeout=10, trust_env=False) as client:
                mid = seed_demo(client, 4)
            env = {**os.environ, "EFFMEET_PHONE_QA_CODE": code, "EFFMEET_PHONE_QA_MEETING": mid}
            tls_args = []
            ca = None
            if args.lan_ip:
                openssl = args.openssl or shutil.which("openssl")
                if not openssl:
                    parser.error("LAN HTTPS requires OpenSSL; pass --openssl PATH")
                ca, leaf, key = make_lan_cert(openssl, args.lan_ip)
                tls_args = ["--host", args.lan_ip, "--ssl-certfile", str(leaf), "--ssl-keyfile", str(key)]
            gateway = subprocess.Popen([sys.executable, str(ROOT / "apps" / "web" / "qa" / "gateway.py"),
                                        "--upstream", upstream, "--port", str(args.gateway_port), *tls_args],
                                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            gateway_base = (f"https://{args.lan_ip}:{args.gateway_port}" if args.lan_ip
                            else f"http://127.0.0.1:{args.gateway_port}")
            wait_for(gateway_base + "/qa/login", verify=str(ca) if ca else True)
            if args.lan_ip:
                print("PHONE QA LAN HTTPS:", gateway_base + "/app/?meeting_id=" + mid, flush=True)
                print("Phone trust certificate (public cert only):", ca.parent / "effmeet2-qa-root.cer", flush=True)
                print("Install/trust this test CA on the phone before opening the link. Do NOT share root.key.", flush=True)
            elif args.local_check_only:
                print("LOCAL GATEWAY CHECK ONLY: not HTTPS, not usable as a phone acceptance URL.", flush=True)
                print("Gateway:", gateway_base, flush=True)
            else:
                tunnel = subprocess.Popen([str(binary), "tunnel", "--url", gateway_base, "--protocol", "http2"],
                                          cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          text=True, encoding="utf-8", errors="replace", creationflags=flags)
                base = tunnel_url(tunnel)
                wait_for(base + "/qa/login", seconds=35)
                if tunnel.poll() is not None:
                    raise RuntimeError("HTTPS tunnel exited before public endpoint check")
                print("PHONE QA HTTPS:", base + "/app/?meeting_id=" + mid, flush=True)
            print("Temporary access code:", code, flush=True)
            print("Synthetic meeting:", mid, flush=True)
            print("Remote identity: remote_1 only. Four artificial candidates expire after 120 seconds.", flush=True)
            print("The address and code work only while this process runs. Ctrl+C shuts everything down.", flush=True)
            while True:
                if controller.poll() is not None or gateway.poll() is not None or (tunnel and tunnel.poll() is not None):
                    raise RuntimeError("a preview subprocess exited; check the temporary controller log")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Phone QA preview stopped.", flush=True)
        finally:
            stop(tunnel)
            stop(gateway)
            stop(controller)


if __name__ == "__main__":
    main()
