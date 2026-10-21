"""Create a ModelScope Studio and push a local directory to it.

Requires MODELSCOPE_API_KEY with Studio/OpenAPI permissions.

  python scripts/deploy_modelscope.py whoami
  python scripts/deploy_modelscope.py deploy --dir site --repo effmeetbot --sdk static --public
  python scripts/deploy_modelscope.py deploy --dir apps/ai-demo --repo effmeetbot-ai --sdk gradio --public
  python scripts/deploy_modelscope.py secret --repo effmeetbot-ai --key QWEN_API_KEY
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

ENDPOINT = os.environ.get("MODELSCOPE_ENDPOINT", "https://modelscope.cn").rstrip("/")
API = f"{ENDPOINT}/openapi/v1"


def token() -> str:
    value = os.environ.get("MODELSCOPE_API_KEY", "").strip()
    if not value:
        raise SystemExit("MODELSCOPE_API_KEY is not set")
    return value


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}


def call(method: str, path: str, payload: dict | None = None) -> dict:
    response = requests.request(method, API + path, headers=headers(), json=payload, timeout=60)
    try:
        data = response.json()
    except ValueError:
        raise SystemExit(f"{method} {path} -> {response.status_code}: {response.text[:300]}")
    if response.status_code >= 400 or not data.get("success", False):
        raise SystemExit(f"{method} {path} -> {response.status_code}: {data}")
    return data.get("data") or {}


def whoami() -> dict:
    return call("GET", "/users/me")


def create_or_get(owner: str, repo: str, sdk: str, public: bool, display_name: str) -> dict:
    try:
        return call("GET", f"/studios/{owner}/{repo}")
    except SystemExit:
        pass
    payload = {
        "owner": owner,
        "repo_name": repo,
        "sdk_type": sdk,
        "visibility": "public" if public else "private",
        "display_name": display_name,
    }
    if sdk == "gradio":
        payload["hardware"] = "platform/2v-cpu-16g-mem"
    return call("POST", "/studios", payload)


def git_push(directory: Path, owner: str, repo: str) -> None:
    key = token()
    work = Path(tempfile.mkdtemp(prefix="ms-studio-"))
    target = work / repo
    shutil.copytree(directory, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "tests"))
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    run = lambda *args: subprocess.run(list(args), cwd=target, check=True, env=env)
    run("git", "init", "-b", "master")
    run("git", "config", "user.name", "effmeetbot-deploy")
    run("git", "config", "user.email", "deploy@effmeetbot.local")
    run("git", "add", "-A")
    run("git", "commit", "-m", "Deploy to ModelScope Studio")
    host = ENDPOINT.split("://", 1)[1]
    run("git", "remote", "add", "origin", f"https://oauth2:{key}@{host}/studios/{owner}/{repo}.git")
    run("git", "push", "-u", "origin", "master")


def deploy(owner: str, repo: str) -> dict:
    return call("POST", f"/studios/{owner}/{repo}/deploy")


def set_secret(owner: str, repo: str, key: str) -> None:
    value = os.environ.get(key, "").strip()
    if not value:
        raise SystemExit(f"{key} is not set in the environment")
    call("POST", f"/studios/{owner}/{repo}/secrets", {"key": key, "value": value})


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami")

    d = sub.add_parser("deploy")
    d.add_argument("--dir", required=True)
    d.add_argument("--repo", required=True)
    d.add_argument("--sdk", choices=["static", "gradio"], required=True)
    d.add_argument("--owner", default="")
    d.add_argument("--display-name", default="在议 · effmeetbot")
    d.add_argument("--public", action="store_true")

    s = sub.add_parser("secret")
    s.add_argument("--repo", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--owner", default="")

    args = parser.parse_args()
    if args.command == "whoami":
        print(whoami())
        return

    owner = args.owner or whoami().get("username") or whoami().get("Username")
    if not owner:
        raise SystemExit("cannot resolve ModelScope username")
    repo = args.repo

    if args.command == "secret":
        set_secret(owner, repo, args.key)
        print(f"secret {args.key} set for {owner}/{repo}")
        return

    directory = Path(args.dir).resolve()
    if not directory.is_dir():
        raise SystemExit(f"not a directory: {directory}")
    info = create_or_get(owner, repo, args.sdk, args.public, args.display_name)
    print("studio:", info.get("url") or f"{ENDPOINT}/studios/{owner}/{repo}")
    git_push(directory, owner, repo)
    deploy(owner, repo)
    print(f"deployed: {ENDPOINT}/studios/{owner}/{repo}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(f"git command failed: {exc}")
