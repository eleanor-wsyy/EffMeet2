"""Local-only demo API. Simulated identities are NOT a production login system."""
import os
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import secrets
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Body, FastAPI, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from .contracts import DemoError, ROOT, validate
from .store import Store


def create_app(db_path=None, *, analyzer=None, robot=None, clock=time.time, candidate_ttl=120, bench=False, asr=None, tts=None):
    bench = bench or os.getenv("EFFMEET_BENCH") == "1"
    configured = db_path or os.getenv("EFFMEET_DB_PATH") or ROOT / "data/demo.sqlite3"
    runtime = None
    if bench:
        from .bench import Bench, DeferredRobot
        from .qwen_client import create_analyzer
        from services.relay.asr import FunASR
        from services.relay.tts import WindowsTTS
        store = Store(configured, robot=DeferredRobot(), clock=clock, candidate_ttl=candidate_ttl, bench=True)
        if asr is None and os.getenv("FUNASR_WS_URL"):
            asr = FunASR(os.environ["FUNASR_WS_URL"])
        if tts is None and os.getenv("EFFMEET_TTS") == "windows":
            tts = WindowsTTS()
        runtime = Bench(store, analyzer or create_analyzer(), tts)
    else:
        store = Store(configured, analyzer=analyzer, robot=robot, clock=clock, candidate_ttl=candidate_ttl)
    profiles = [
        {"actor": "operator", "label": "主持人 / 调试", "token": secrets.token_urlsafe(24)},
        {"actor": "remote_1", "label": "线上成员 1", "token": secrets.token_urlsafe(24)},
        {"actor": "remote_2", "label": "线上成员 2", "token": secrets.token_urlsafe(24)},
    ]
    tokens = {x["token"]: x["actor"] for x in profiles}

    @asynccontextmanager
    async def lifespan(app):
        task = None
        if runtime:
            runtime.recover()
            task = asyncio.create_task(runtime.worker())
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="EffMeet 2 · 本机台架" if bench else "EffMeet 2 · 无硬件模拟闭环", version="0.2.0", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.store = store
    app.state.robot = store.robot
    app.state.bench = runtime

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
            # Allow larger bodies only for the multipart capture upload route.
            # Multipart parsers may expose a trailing slash or a mounted path;
            # accept only these two explicitly bounded media routes.
            if not ("/captures" in request.url.path or "/audio-upload" in request.url.path):
                return error(413, "BODY_TOO_LARGE", "模拟请求不能超过16KiB。")
            if int(request.headers.get("content-length", "0")) > 2 * 1024 * 1024:
                return error(413, "MEDIA_TOO_LARGE", "图片或音频不能超过2MiB。")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' blob:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'"
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
        return HTMLResponse((Path(__file__).parent / ("bench.html" if bench else "demo.html")).read_text(encoding="utf-8"))

    @app.get("/bench-camera.js", include_in_schema=False)
    def camera_script():
        return Response(Path(__file__).with_name("camera.js").read_text(encoding="utf-8"), media_type="text/javascript")

    @app.get("/bench-audio.js", include_in_schema=False)
    def audio_script():
        return Response(Path(__file__).with_name("audio.js").read_text(encoding="utf-8"), media_type="text/javascript")

    @app.get("/healthz")
    def health():
        if runtime:
            return {"ok": True, "mode": "bench", "hardware_connected": False,
                "model_adapter": getattr(runtime.analyzer, "label", "qwen" if runtime.analyzer.mode == "real" else "not_configured"),
                "audio_capture": False, "asr_configured": asr is not None, "tts_configured": tts is not None}
        return {"ok": True, "mode": "mock", "hardware_connected": False,
                "model_adapter": "fake", "audio_capture": False}

    @app.get("/api/demo/session", include_in_schema=False)
    def demo_session():
        return {"mode": "bench" if bench else "mock", "profiles": profiles,
                "warning": "本机调试身份选择器；不是正式账号认证。台架模式按配置调用ASR、模型和播放器。"}

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
        result = store.add_utterance(meeting_id, body, mode="manual" if bench else "mock")
        return JSONResponse(result, status_code=200 if result["replayed"] else 201)

    @app.post("/api/v1/meetings/{meeting_id}/captures", status_code=201)
    async def upload_capture(meeting_id: str, request: Request, file: UploadFile,
                             source: Literal["file_upload", "browser_camera"] = Query("file_upload")):
        operator(request)
        content_type = file.content_type or ""
        if content_type not in {"image/jpeg", "image/png"}:
            raise DemoError(422, "INVALID_CONTENT_TYPE", "只接受 JPEG 或 PNG 图片。")
        data = await file.read(2 * 1024 * 1024 + 1)
        await file.close()
        if len(data) > 2 * 1024 * 1024:
            raise DemoError(413, "CAPTURE_TOO_LARGE", "图片不能超过2MiB。")
        if not data:
            raise DemoError(422, "EMPTY_FILE", "文件内容为空。")
        signature = b"\xff\xd8\xff" if content_type == "image/jpeg" else b"\x89PNG\r\n\x1a\n"
        if not data.startswith(signature):
            raise DemoError(422, "INVALID_IMAGE", "图片文件头与声明格式不一致。")
        filename = file.filename or "capture.jpg"
        return store.add_capture(meeting_id, filename, content_type, data,
                                 mode="manual" if bench else "mock",
                                 source=source if bench else "demo_capture")

    if runtime:
        @app.post("/api/bench/meetings/{meeting_id}/audio-upload", status_code=201)
        async def upload_audio(meeting_id: str, request: Request, file: UploadFile,
                               speaker_id: str = Query("onsite_1"), channel: Literal["onsite", "remote"] = Query("onsite")):
            operator(request)
            if asr is None:
                raise DemoError(503, "ASR_NOT_CONFIGURED", "未配置 FunASR。")
            if file.content_type not in {"audio/wav", "audio/x-wav", "application/octet-stream"}:
                raise DemoError(422, "INVALID_AUDIO_TYPE", "只接受 WAV PCM 音频。")
            import io, wave
            data = await file.read(960044)
            try:
                with wave.open(io.BytesIO(data), "rb") as wav:
                    if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
                        raise ValueError
                    pcm = wav.readframes(wav.getnframes())
            except (wave.Error, ValueError):
                raise DemoError(422, "INVALID_WAV", "WAV 必须是16kHz、单声道、16-bit PCM，最长30秒。")
            if not 2 <= len(pcm) <= 960000:
                raise DemoError(422, "INVALID_WAV", "音频长度必须在1至30秒之间。")
            with store.db() as conn:
                store.require_meeting(conn, meeting_id)
            text = await asr.transcribe(pcm, str(uuid4()))
            if not text:
                raise DemoError(422, "EMPTY_TRANSCRIPT", "未识别到有效发言。")
            utterance = {"utterance_id": str(uuid4()), "stream_id": "browser_mic", "speaker_id": speaker_id,
                "channel": channel, "start_ms": 0, "end_ms": len(pcm) // 32, "text": text, "final": True, "revision": 1}
            return store.add_utterance(meeting_id, utterance, mode=asr.mode, source="browser_microphone", producer="asr")

        @app.post("/api/bench/meetings/{meeting_id}/captures/{capture_id}/vision")
        async def analyze_capture_vision(meeting_id: str, capture_id: str, request: Request):
            operator(request)
            row = store.get_capture(meeting_id, capture_id)
            if not hasattr(runtime.analyzer, "analyze_image"):
                raise DemoError(503, "QWEN_VISION_UNAVAILABLE", "当前模型适配器不支持图片识别。")
            text = await asyncio.to_thread(runtime.analyzer.analyze_image, row["data"], row["content_type"])
            return {"meeting_id": meeting_id, "capture_id": capture_id, "model": os.getenv("QWEN_VL_MODEL", "qwen-vl-max"), "text": text, "source": "qwen_vision", "mode": "real"}

    @app.get("/api/v1/meetings/{meeting_id}/captures")
    def list_captures(meeting_id: str, request: Request):
        actor(request)
        return store.list_captures(meeting_id)

    @app.get("/api/v1/meetings/{meeting_id}/captures/{capture_id}")
    def get_capture(meeting_id: str, capture_id: str, request: Request):
        actor(request)
        row = store.get_capture(meeting_id, capture_id)
        from fastapi.responses import Response
        return Response(content=row["data"], media_type=row["content_type"])

    @app.post("/api/v1/meetings/{meeting_id}/audio/sessions", status_code=201)
    def open_audio_session(meeting_id: str, request: Request, body: dict = Body(...)):
        operator(request)
        return store.open_audio_session(meeting_id, body)

    @app.post("/api/v1/meetings/{meeting_id}/audio/sessions/end", status_code=202)
    def end_audio_session(meeting_id: str, request: Request, body: dict = Body(...)):
        operator(request)
        return store.end_audio_session(meeting_id, body)

    @app.post("/api/v1/meetings/{meeting_id}/devices/{device_id}/pair", status_code=201)
    def pair_device(meeting_id: str, device_id: str, request: Request):
        operator(request)
        return store.pair_device(meeting_id, device_id)

    @app.post("/api/v1/meetings/{meeting_id}/analysis", status_code=202)
    def analyze(meeting_id: str, request: Request, body: dict = Body(...),
                mock_status: Literal["possibly_unresponded", "responded", "uncertain"] = Query("possibly_unresponded")):
        operator(request)
        if runtime:
            return runtime.enqueue(meeting_id, body)
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

    @app.post("/api/v1/meetings/{meeting_id}/viewpoint-map", status_code=202)
    def build_viewpoint_map(meeting_id: str, request: Request, body: dict = Body(...)):
        operator(request)
        validate("EmptyRequest", body)
        return store.build_viewpoint_map(meeting_id)

    @app.get("/api/v1/meetings/{meeting_id}/viewpoint-map")
    def read_viewpoint_map(meeting_id: str, request: Request):
        actor(request)
        return store.build_viewpoint_map(meeting_id)

    @app.post("/api/v1/meetings/{meeting_id}/summary", status_code=202)
    def build_summary(meeting_id: str, request: Request, body: dict = Body(...)):
        operator(request)
        validate("EmptyRequest", body)
        return store.build_summary(meeting_id)

    @app.get("/api/v1/meetings/{meeting_id}/summary")
    def read_summary(meeting_id: str, request: Request):
        actor(request)
        return store.read_summary(meeting_id)

    if runtime:
        from services.relay.media import install_media
        install_media(app, runtime, asr)

        @app.get("/api/bench/meetings/{meeting_id}/response-tracking")
        def response_tracking(meeting_id: str, request: Request):
            actor(request)
            return store.response_tracking(meeting_id)

        @app.post("/api/bench/meetings/{meeting_id}/claims/{claim_id}/response-verification")
        async def verify_response(meeting_id: str, claim_id: str, request: Request, body: dict = Body(...)):
            result = store.verify_response(meeting_id, claim_id, body, actor(request))
            for cid in result["cancel_commands"]:
                if cid in runtime.active:
                    runtime.active[cid].set()
                runtime.fail_command(cid, "RESPONSE_VERIFIED")
            return result

        @app.post("/api/bench/meetings/{meeting_id}/media-bindings", status_code=201)
        def bind_media(meeting_id: str, request: Request, body: dict = Body(...)):
            operator(request)
            return runtime.bind(meeting_id, body)

        @app.get("/api/bench/meetings/{meeting_id}/jobs/{job_id}")
        def get_job(meeting_id: str, job_id: str, request: Request):
            operator(request)
            return runtime.job(meeting_id, job_id)

        @app.post("/api/bench/commands/{command_id}/stop", status_code=202)
        async def stop_command(command_id: str, request: Request):
            identity = actor(request)
            row = runtime.command(command_id)
            with store.db() as conn:
                owner = conn.execute("SELECT owner FROM interventions WHERE id=?", (row["intervention_id"],)).fetchone()[0]
            if identity not in {"operator", owner}:
                raise DemoError(403, "NOT_OWNER", "只能停止自己的提示。")
            signal = runtime.active.get(command_id)
            if signal:
                signal.set()
            runtime.fail_command(command_id, "CANCELLED")
            return {"command_id": command_id, "state": runtime.command(command_id)["state"]}

    @app.websocket("/api/v1/meetings/{meeting_id}/events")
    async def event_stream(ws: WebSocket, meeting_id: str):
        if (ws.client.host not in {"127.0.0.1", "::1", "testclient"} or ws.query_params
                or (ws.headers.get("origin") and ws.headers["origin"] != "http://" + ws.headers.get("host", ""))):
            await ws.close(code=4403)
            return
        await ws.accept()
        try:
            hello = await asyncio.wait_for(ws.receive_json(), 5)
            if hello.get("token") not in tokens:
                await ws.close(code=4401)
                return
            seq = hello.get("after_seq", 0)
            if type(seq) is not int or seq < 0:
                await ws.close(code=4400)
                return
            while True:
                for event in store.events(meeting_id, seq):
                    await ws.send_json(event)
                    seq = event["seq"]
                try:
                    message = await asyncio.wait_for(ws.receive(), 0.2)
                    if message["type"] == "websocket.disconnect":
                        return
                except TimeoutError:
                    pass
        except (WebSocketDisconnect, TimeoutError, DemoError, ValueError, TypeError, AttributeError):
            with suppress(RuntimeError):
                await ws.close(code=4400)

    return app
