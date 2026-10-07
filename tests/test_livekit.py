import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from services.controller.store import Store
from services.relay.livekit_bridge import RemoteIngest
from services.relay.livekit_token import issue_token


class LiveKitTests(unittest.TestCase):
    def test_stream_segments_are_drained_and_closed(self):
        import struct
        import time
        from types import SimpleNamespace
        from services.relay.livekit_bridge import LiveKitBridge
        from livekit import rtc
        class Stream:
            closed = False
            def __init__(self, *args, **kwargs):
                self.frames = iter([struct.pack('<h', 1000)*320]*5 + [bytes(640)]*40)
            def __aiter__(self):
                return self
            async def __anext__(self):
                await asyncio.sleep(0)
                try:
                    return SimpleNamespace(frame=SimpleNamespace(data=next(self.frames)))
                except StopIteration:
                    raise StopAsyncIteration
            async def aclose(self):
                self.closed = True
        async def check():
            bridge = LiveKitBridge(None, None)
            bridge.epochs['meeting'] = time.monotonic()
            bridge.ingest.ingest = AsyncMock()
            stream = Stream()
            with patch.object(rtc, 'AudioStream', return_value=stream):
                await bridge.consume('meeting', 'remote_1', object())
            self.assertTrue(stream.closed)
            self.assertEqual(bridge.ingest.ingest.await_count, 1)
            args = bridge.ingest.ingest.await_args.args
            self.assertEqual(args[1], 'remote_1')
            self.assertEqual(len(args[4]), 45*640)
        asyncio.run(check())

    def test_microphone_only_grants(self):
        import jwt
        with patch.dict(os.environ, {'LIVEKIT_API_KEY': 'test', 'LIVEKIT_API_SECRET': 'a'*32,
                                    'LIVEKIT_URL': 'ws://localhost:7880'}):
            value = issue_token('meeting', 'remote_1')
            claims = jwt.decode(value['token'], 'a'*32, algorithms=['HS256'])
            self.assertEqual(claims['sub'], 'remote_1')
            self.assertEqual(claims['video']['room'], 'meeting')
            self.assertEqual(claims['video']['canPublishSources'], ['microphone'])
            relay = jwt.decode(issue_token('meeting', 'relay', relay=True)['token'],
                               'a'*32, algorithms=['HS256'])
            self.assertFalse(relay['video']['canPublish'])

    def test_remote_ledger_idempotency_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'test.sqlite3')
            meeting = store.create_meeting({'title': 'LiveKit test'})['meeting_id']
            asr = type('ASR', (), {'mode': 'mock', 'transcribe': AsyncMock(return_value='远程观点')})()
            ingest = RemoteIngest(store, asr)
            async def check():
                a = await ingest.ingest(meeting, 'remote_1', 'track', 'segment', bytes(3200), 100)
                b = await ingest.ingest(meeting, 'remote_1', 'track', 'segment', bytes(3200), 100)
                self.assertEqual(a['event'], b['event'])
                with self.assertRaises(ValueError):
                    await ingest.ingest(meeting, 'operator', 'track', 'bad', bytes(3200), 0)
            asyncio.run(check())

    def test_token_endpoint_identity_and_missing_config(self):
        from fastapi.testclient import TestClient
        from services.controller.app import create_app
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            with TestClient(create_app(db_path=Path(tmp)/'test.sqlite3')) as client:
                profiles = client.get('/api/demo/session').json()['profiles']
                headers = {'Authorization': 'Bearer '+profiles[1]['token']}
                mid = client.post('/api/v1/meetings', json={'title':'test'},
                                  headers={'Authorization':'Bearer '+profiles[0]['token']}).json()['meeting_id']
                path = f'/api/v1/meetings/{mid}/livekit-token'
                self.assertEqual(client.post(path, json={'identity':'remote_2'},headers=headers).status_code,403)
                self.assertEqual(client.post(path,json={},headers=headers).status_code,503)
