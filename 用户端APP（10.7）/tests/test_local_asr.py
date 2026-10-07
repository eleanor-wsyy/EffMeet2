"""Wire validation tests without downloading or loading speech models."""
import asyncio
import json
import unittest
from scripts.run_local_asr import handle


class Socket:
    def __init__(self, config, messages):
        self.config, self.messages, self.output = config, iter(messages), []
        self.closed = None

    async def recv(self):
        return json.dumps(self.config)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, value):
        self.output.append(json.loads(value))

    async def close(self, **kwargs):
        self.closed = kwargs


class LocalASRTests(unittest.IsolatedAsyncioTestCase):
    config = {"mode": "offline", "wav_name": "test", "wav_format": "pcm",
              "audio_fs": 16000, "is_speaking": True}

    async def test_valid_pcm_once(self):
        calls = []
        def infer(pcm):
            calls.append(pcm)
            return "测试替身"
        ws = Socket(self.config, [bytes(640), '{"is_speaking":false}'])
        await handle(ws, infer, asyncio.Lock())
        self.assertEqual(calls, [bytes(640)])
        self.assertEqual(ws.output[0]["text"], "测试替身")
        self.assertEqual(ws.output[0]["wav_name"], "test")

    async def test_invalid_input_never_infers(self):
        def infer(pcm):
            self.fail("Invalid input reached model")
        for config, messages in [
            ({**self.config, "audio_fs": 8000}, []),
            (self.config, [b"a"]),
            (self.config, [bytes(960002)]),
            (self.config, ['{"is_speaking":false}']),
            (self.config, ['{"unexpected":true}']),
        ]:
            ws = Socket(config, messages)
            await handle(ws, infer, asyncio.Lock())
            self.assertEqual(ws.closed["code"], 1008)

    async def test_busy_rejected(self):
        lock = asyncio.Lock()
        await lock.acquire()
        ws = Socket(self.config, [bytes(640), '{"is_speaking":false}'])
        await handle(ws, lambda pcm: self.fail("Busy model called"), lock)
        self.assertEqual(ws.closed["reason"], "ASR_BUSY")
