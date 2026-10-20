"""LAN device gateway: exposes only the device-facing routes on the network.

The controller stays bound to 127.0.0.1. This gateway proxies only:
  - GET  /healthz
  - WS   /device/v1/audio, /device/v1/playback
  - WS   /api/v1/meetings/{meeting_id}/events
Everything else returns 404. Use it on an isolated demo network only.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import re
from typing import Optional

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

# Only these WS routes may ever be forwarded to the upstream controller.
WS_ALLOWED = re.compile(r"^(?:/device/v1/(?:audio|playback)|/api/v1/meetings/[0-9a-fA-F-]{36}/events)$")
HTTP_PATHS = {"healthz"}


def _ws_url(upstream: str, path: str, query: str = "") -> str:
    if not upstream.startswith(("http://127.0.0.1", "http://localhost")):
        raise ValueError("upstream must be loopback")
    return upstream.replace("http://", "ws://", 1) + path + query


def create_device_gateway(upstream: str, *, transport: Optional[httpx.BaseTransport] = None):
    client = httpx.AsyncClient(base_url=upstream, transport=transport, timeout=30,
                               trust_env=False)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await client.aclose()

    app = FastAPI(title="EffMeet2 device gateway", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz")
    async def healthz():
        result = await client.get("/healthz")
        return Response(content=result.content, status_code=result.status_code,
                        headers={"Content-Type": result.headers.get("content-type", "application/json")})

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"])
    async def http_proxy(request: Request, path: str):
        if path not in HTTP_PATHS:
            return Response(status_code=404)
        headers = {}
        auth = request.headers.get("authorization")
        if auth:
            headers["Authorization"] = auth
        body = await request.body()
        if body:
            headers["Content-Type"] = request.headers.get("content-type", "application/json")
        result = await client.request(request.method, "/" + path, params=dict(request.query_params),
                                      headers=headers, content=body)
        return Response(content=result.content, status_code=result.status_code,
                        headers={"Content-Type": result.headers.get("content-type", "application/json")})

    @app.websocket("/{path:path}")
    async def ws_proxy(websocket: WebSocket, path: str):
        normalized = "/" + path
        if not WS_ALLOWED.fullmatch(normalized):
            await websocket.accept()
            await websocket.close(code=1008)
            return
        query = websocket.scope.get("query_string", b"")
        query = ("?" + query.decode()) if query else ""
        headers = {}
        auth = websocket.headers.get("authorization")
        if auth:
            headers["Authorization"] = auth
        await websocket.accept()
        from websockets.asyncio.client import connect
        try:
            async with connect(_ws_url(upstream, normalized, query),
                               additional_headers=headers) as upstream_ws:
                async def to_upstream():
                    try:
                        while True:
                            message = await websocket.receive()
                            if message["type"] == "websocket.disconnect":
                                return
                            if message.get("text") is not None:
                                await upstream_ws.send(message["text"])
                            elif message.get("bytes") is not None:
                                await upstream_ws.send(message["bytes"])
                    except WebSocketDisconnect:
                        return
                    finally:
                        await upstream_ws.close()

                async def to_client():
                    try:
                        async for message in upstream_ws:
                            if isinstance(message, bytes):
                                await websocket.send_bytes(message)
                            else:
                                await websocket.send_text(message)
                    except WebSocketDisconnect:
                        pass
                    finally:
                        await websocket.close()

                await asyncio.gather(to_upstream(), to_client())
        except Exception:
            with suppress(Exception):
                await websocket.close()

    return app
