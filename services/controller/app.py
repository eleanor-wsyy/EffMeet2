"""Local-only demo API. Simulated identities are NOT a production login system."""
import os
from pathlib import Path
import secrets
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Body, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException

from .contracts import DemoError, ROOT, validate
from .store import Store


def create_app(db_path=None, *, analyzer=None, robot=None, clock=time.time, candidate_ttl=120):
    configured = db_path or os.getenv("EFFMEET_DB_PATH") or ROOT / "data/demo.sqlite3"
    store = Store(configured, analyzer=analyzer, robot=robot, clock=clock, candidate_ttl=candidate_ttl)
    profiles = [
        {"actor": "operator", "label": "主持人 / 调试", "token": secrets.token_urlsafe(24)},
        {"actor": "remote_1", "label": "线上成员 1", "token": secrets.token_urlsafe(24)},
        {"actor": "remote_2", "label": "线上成员 2", "token": secrets.token_urlsafe(24)},
    ]
    tokens = {x["token"]: x["actor"] for x in profiles}

    app = FastAPI(title="EffMeet 2 · 无硬件模拟闭环", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.store = store
    app.state.robot = store.robot

    def error(status, code, message):
        body = {"error": {"code": code, "message": message, "retryable": False, "trace_id": str(uuid4())}}
        validate("ErrorResponse", body)
        return JSONResponse(body, status_code=status)

    @app.middleware("http")
    async def local_only(request, call_next):
        if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return error(403, "LOCAL_ONLY", "此模拟应用仅允许本机访问。")
        host = request.headers.get("host", "")
        try:
            hostname = urlsplit("http://" + host).hostname
        except ValueError:
            hostname = None
        if hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return error(403, "LOCAL_ONLY", "此模拟应用仅允许本机访问。")
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{host}":
            return error(403, "BAD_ORIGIN", "拒绝跨站请求本机模拟服务。")
        if request.headers.get("content-length", "0").isdigit() and int(request.headers.get("content-length", "0")) > 16384:
            return error(413, "BODY_TOO_LARGE", "模拟请求不能超过16KiB。")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.exception_handler(DemoError)
    async def domain_error(request, exc):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        return error(422, "INVALID_REQUEST", "请求格式或查询参数不正确。")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(exc.status_code, "HTTP_ERROR", str(exc.detail))

    def actor(request):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] not in tokens:
            raise DemoError(401, "UNAUTHORIZED", "需要本机模拟会话凭据。")
        return tokens[auth[7:]]

    def operator(request):
        identity = actor(request)
        if identity != "operator":
            raise DemoError(403, "OPERATOR_ONLY", "该操作由主持人/调试入口执行。")
        return identity

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index():
        return HTMLResponse((Path(__file__).parent / "demo.html").read_text(encoding="utf-8"))

    @app.get("/healthz")
    def health():
        return {"ok": True, "mode": "mock", "hardware_connected": False,
                "model_adapter": "fake", "audio_capture": False}

    @app.get("/api/demo/session", include_in_schema=False)
    def demo_session():
        return {"mode": "mock", "profiles": profiles,
                "warning": "本机调试身份选择器；不是正式账号认证，不连接真实机器人或模型。"}

    @app.post("/api/v1/meetings", status_code=201)
    def create_meeting(request: Request, body: dict = Body(...)):
        operator(request)
        return store.create_meeting(body)

    @app.post("/api/v1/meetings/{meeting_id}/utterances")
    def add_utterance(meeting_id: str, request: Request, body: dict = Body(...)):
        identity = actor(request)
        validate("UtteranceFinal", body)
        if identity != "operator" and (body["channel"] != "remote" or body["speaker_id"] != identity):
            raise DemoError(403, "SPEAKER_MISMATCH", "模拟线上会话不能替别人提交发言。")
        result = store.add_utterance(meeting_id, body)
        return JSONResponse(result, status_code=200 if result["replayed"] else 201)

    @app.post("/api/v1/meetings/{meeting_id}/analysis", status_code=202)
    def analyze(meeting_id: str, request: Request, body: dict = Body(...),
                mock_status: Literal["possibly_unresponded", "responded", "uncertain"] = Query("possibly_unresponded")):
        operator(request)
        return store.analyze(meeting_id, body, mock_status)

    @app.post("/api/v1/meetings/{meeting_id}/interventions/{intervention_id}/decision", status_code=202)
    def decide(meeting_id: str, intervention_id: str, request: Request, body: dict = Body(...)):
        identity = actor(request)
        return store.decide(meeting_id, intervention_id, body, identity)

    @app.get("/api/demo/meetings/{meeting_id}/state", include_in_schema=False)
    def state(meeting_id: str, request: Request):
        actor(request)
        return store.snapshot(meeting_id)

    @app.get("/api/v1/meetings/{meeting_id}/events")
    def events(meeting_id: str, request: Request, after_seq: int = Query(0, ge=0)):
        actor(request)
        return store.events(meeting_id, after_seq)

    @app.post("/api/v1/meetings/{meeting_id}/summary", status_code=202)
    def build_summary(meeting_id: str, request: Request, body: dict = Body(...)):
        operator(request)
        validate("EmptyRequest", body)
        return store.build_summary(meeting_id)

    @app.get("/api/v1/meetings/{meeting_id}/summary")
    def read_summary(meeting_id: str, request: Request):
        actor(request)
        return store.read_summary(meeting_id)

    return app
