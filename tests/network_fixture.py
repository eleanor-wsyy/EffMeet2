"""Explicit synthetic providers for the real-TCP integration test only."""
import json
import os
import time
from fastapi import WebSocket
from services.controller.app import create_app
from services.controller.fakes import FakeAnalyzer
from services.relay.asr import FunASR


class Model:
    mode = "real"
    label = "synthetic_fixture（合成测试）"
    def analyze(self, evidence, status):
        time.sleep(.2)
        return FakeAnalyzer().analyze(evidence, "possibly_unresponded")


class TTS:
    def synthesize(self, text):
        return bytes(3200)


asr = FunASR(f"ws://127.0.0.1:{os.environ['EFFMEET_FIXTURE_PORT']}/fixture/funasr")
asr.mode = "mock"
if os.getenv('EFFMEET_REAL_TTS_TEST') == '1':
    from services.relay.tts import WindowsTTS
    tts = WindowsTTS()
else:
    tts = TTS()
app = create_app(bench=True, asr=asr, analyzer=Model(), tts=tts)


@app.websocket("/fixture/funasr")
async def fixture_asr(ws: WebSocket):
    await ws.accept()
    config = await ws.receive_json()
    assert config["mode"] == "offline" and config["audio_fs"] == 16000
    total = 0
    while True:
        message = await ws.receive()
        if message.get("bytes") is not None:
            total += len(message["bytes"])
        elif json.loads(message["text"])["is_speaking"] is False:
            assert total > 0 and total % 2 == 0
            await ws.send_json({"mode": "offline", "wav_name": config["wav_name"],
                "is_final": False, "text": "合成测试：先验证草图。"})
            await ws.close()
            return


if __name__ == "__main__":
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=int(os.environ["EFFMEET_FIXTURE_PORT"]), ws_max_size=65536))
    @app.post("/fixture/shutdown")
    def shutdown():
        server.should_exit = True
        return {"stopping": True}
    server.run()
