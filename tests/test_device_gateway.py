import asyncio
import queue
import socket
import threading
import time
import unittest

import httpx
import websockets
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from services.device_gateway import create_device_gateway


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_uvicorn(app):
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                            access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    return port, server


def _start_echo_ws():
    result = queue.Queue()

    async def echo(ws):
        async for message in ws:
            await ws.send(message)

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def main():
            server = await websockets.serve(echo, "127.0.0.1", 0)
            result.put(server.sockets[0].getsockname()[1])
            await asyncio.Event().wait()

        try:
            loop.run_until_complete(main())
        except Exception:
            result.put(None)

    threading.Thread(target=run, daemon=True).start()
    port = result.get(timeout=10)
    if port is None:
        raise RuntimeError("echo server failed to start")
    return port


class DeviceGatewayTests(unittest.TestCase):
    def test_http_allowlist_only_forwards_healthz(self):
        upstream = FastAPI()

        @upstream.get("/healthz")
        def healthz():
            return {"ok": True, "upstream": True}

        @upstream.post("/api/v1/meetings")
        def meetings():
            return {"should_not": "be proxied"}

        gateway = create_device_gateway("http://upstream", transport=httpx.ASGITransport(app=upstream))
        with TestClient(gateway) as client:
            self.assertEqual(client.get("/healthz").json(), {"ok": True, "upstream": True})
            self.assertEqual(client.post("/api/v1/meetings", json={}).status_code, 404)
            self.assertEqual(client.get("/api/demo/session").status_code, 404)

    def test_websocket_relay_forwards_text_and_binary(self):
        echo_port = _start_echo_ws()
        gateway_port, server = _start_uvicorn(create_device_gateway(f"http://127.0.0.1:{echo_port}"))

        async def check():
            async with websockets.connect(f"ws://127.0.0.1:{gateway_port}/device/v1/audio") as ws:
                await ws.send("hello")
                self.assertEqual(await ws.recv(), "hello")
                await ws.send(b"\x01\x02")
                self.assertEqual(await ws.recv(), b"\x01\x02")

        try:
            asyncio.run(check())
        finally:
            server.should_exit = True

    def test_websocket_rejects_non_device_path(self):
        echo_port = _start_echo_ws()
        gateway_port, server = _start_uvicorn(create_device_gateway(f"http://127.0.0.1:{echo_port}"))

        async def check():
            async with websockets.connect(f"ws://127.0.0.1:{gateway_port}/device/v1/other") as ws:
                with self.assertRaises(websockets.exceptions.ConnectionClosed) as raised:
                    await ws.recv()
                self.assertEqual(raised.exception.code, 1008)

        try:
            asyncio.run(check())
        finally:
            server.should_exit = True
