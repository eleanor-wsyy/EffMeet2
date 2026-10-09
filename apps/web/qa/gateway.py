"""Synthetic-only phone QA gateway. Not production authentication."""
import argparse
from contextlib import asynccontextmanager
import html
import os
import re
import secrets
import time
from uuid import UUID

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

STATIC = {
    "app/", "app/index.html", "app/styles.css", "app/app.js", "app/state.js",
    "app/manifest.json", "app/sw.js",
    *("app/assets/" + name for name in (
        "brand.svg", "enter.svg", "link.svg", "mic-white.svg", "mic.svg", "user.svg",
        "icon-192.png", "icon-512.png", "apple-touch-icon.png")),
}
UUID_RE = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
STATE_RE = re.compile(rf"api/demo/meetings/({UUID_RE})/state\Z")
READ_RE = re.compile(rf"api/v1/meetings/({UUID_RE})/(?:viewpoint-map|captures(?:/({UUID_RE}))?)\Z")
DECIDE_RE = re.compile(rf"api/v1/meetings/({UUID_RE})/interventions/({UUID_RE})/(?:decision|recheck)\Z")
COOKIE = "effmeet_phone_qa"


def create_gateway(upstream, meeting_id, access_code, *, transport=None):
    """Expose one synthetic meeting and one remote identity behind a password cookie."""
    meeting_id = str(UUID(meeting_id))
    if len(access_code) < 24:
        raise ValueError("access code needs at least 24 characters")
    session = secrets.token_urlsafe(32)
    attempts = {}
    remote_token = None
    client = httpx.AsyncClient(base_url=upstream, transport=transport, timeout=12,
                               follow_redirects=False, trust_env=False)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def origin_ok(request):
        origin = request.headers.get("origin")
        if not origin:
            return True  # The unpredictable code/cookie are still required.
        host = request.headers.get("host", "")
        return origin == "https://" + host or (
            request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}
            and origin == "http://" + host)

    def logged_in(request):
        value = request.cookies.get(COOKIE, "")
        return bool(value) and secrets.compare_digest(value, session)

    def login_page(message=""):
        error = f'<p role="alert">{html.escape(message)}</p>' if message else ""
        return HTMLResponse(("""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>EffMeet 手机验收入口</title>
<style>body{font:16px/1.6 system-ui;background:#f6f7f9;color:#24262a;padding:12vh 20px}
main{max-width:390px;margin:auto;background:white;border-radius:20px;padding:24px;box-shadow:0 8px 24px #0001}
label,input,button{display:block;width:100%;box-sizing:border-box}input,button{min-height:48px;margin-top:12px;padding:12px;font:inherit}
button{border:0;border-radius:12px;background:#f0522e;color:white}</style>
<main><h1>手机验收入口</h1><p>仅用于合成会议测试，不要输入真实会议数据。</p>"""
            + error + """<form method="post" action="/qa/login"><label for="code">临时访问口令</label>
<input id="code" name="code" type="password" autocomplete="off" required>
<button>进入测试界面</button></form></main></html>"""),
            headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"})

    async def upstream_session():
        nonlocal remote_token
        result = await client.get("/api/demo/session")
        result.raise_for_status()
        payload = result.json()
        if payload.get("mode") != "mock":
            raise ValueError("phone QA gateway is synthetic/mock-only")
        profiles = [p for p in payload["profiles"] if p["actor"] == "remote_1"]
        if len(profiles) != 1:
            raise ValueError("expected exactly one synthetic participant")
        remote_token = profiles[0]["token"]
        return {**payload, "profiles": profiles,
                "warning": "仅供临时真机界面验收，合成会议；非正式登录、音频或机器人实播。"}

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST"])
    async def route(request: Request, path: str):
        method = request.method
        if path == "qa/login" and method == "GET":
            if logged_in(request):
                return RedirectResponse("/app/?meeting_id=" + meeting_id, status_code=303)
            return login_page()
        if path == "qa/login" and method == "POST":
            if not origin_ok(request):
                return Response(status_code=403)
            ip = request.headers.get("cf-connecting-ip") or request.client.host
            count, since = attempts.get(ip, (0, time.monotonic()))
            if time.monotonic() - since > 900:
                count, since = 0, time.monotonic()
            if count >= 8:
                return Response("稍后再试", status_code=429)
            if len(request.headers.get("content-length", "0")) > 6:
                return Response(status_code=413)
            body = await request.body()
            if len(body) > 2048:
                return Response(status_code=413)
            from urllib.parse import parse_qs
            code = parse_qs(body.decode("utf-8", errors="replace")).get("code", [""])[0]
            if not secrets.compare_digest(code, access_code):
                attempts[ip] = (count + 1, since)
                return login_page("口令不正确")
            attempts.pop(ip, None)
            response = RedirectResponse("/app/?meeting_id=" + meeting_id, status_code=303)
            response.set_cookie(COOKIE, session, secure=True, httponly=True, samesite="strict", max_age=3600, path="/")
            return response
        if not logged_in(request):
            return RedirectResponse("/qa/login", status_code=303) if method in {"GET", "HEAD"} else Response(status_code=401)
        if path == "qa/logout" and method == "POST":
            if not origin_ok(request):
                return Response(status_code=403)
            response = RedirectResponse("/qa/login", status_code=303)
            response.delete_cookie(COOKIE, path="/")
            return response
        if method == "POST" and not origin_ok(request):
            return Response(status_code=403)
        if path == "":
            return RedirectResponse("/app/?meeting_id=" + meeting_id, status_code=303)
        if method in {"GET", "HEAD"}:
            allowed = path in STATIC or path in {"healthz", "api/demo/session"}
            match = STATE_RE.fullmatch(path) or READ_RE.fullmatch(path)
            allowed = allowed or (match is not None and match.group(1) == meeting_id)
        elif method == "POST":
            match = DECIDE_RE.fullmatch(path)
            allowed = match is not None and match.group(1) == meeting_id
        else:
            allowed = False
        if not allowed:
            return Response(status_code=404)
        if path == "api/demo/session":
            try:
                return JSONResponse(await upstream_session())
            except (httpx.HTTPError, ValueError, KeyError):
                return Response("测试服务暂不可用", status_code=502)
        headers = {}
        if path.startswith("api/") and path != "healthz":
            if remote_token is None:
                try:
                    await upstream_session()
                except (httpx.HTTPError, ValueError, KeyError):
                    return Response("测试服务暂不可用", status_code=502)
            auth = request.headers.get("authorization", "")
            if not secrets.compare_digest(auth, "Bearer " + remote_token):
                return Response(status_code=401)
            headers["Authorization"] = auth
        body = await request.body() if method == "POST" else b""
        if len(body) > 16384:
            return Response(status_code=413)
        if body:
            headers["Content-Type"] = "application/json"
        try:
            result = await client.request(method, "/" + path, params=request.query_params,
                                          headers=headers, content=body)
        except httpx.HTTPError:
            return Response("测试服务暂不可用", status_code=502)
        mime = result.headers.get("content-type", "application/octet-stream")
        return Response(content=result.content, status_code=result.status_code,
                        headers={"Content-Type": mime, "Cache-Control": "no-store"})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", default="http://127.0.0.1:8878")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ssl-certfile")
    parser.add_argument("--ssl-keyfile")
    args = parser.parse_args()
    mid = os.environ.get("EFFMEET_PHONE_QA_MEETING", "")
    code = os.environ.get("EFFMEET_PHONE_QA_CODE", "")
    if not mid or not code:
        parser.error("start with run_phone_preview.py, not gateway.py directly")
    import uvicorn
    uvicorn.run(create_gateway(args.upstream, mid, code), host=args.host, port=args.port, ssl_certfile=args.ssl_certfile, ssl_keyfile=args.ssl_keyfile,
                proxy_headers=False, access_log=False)
