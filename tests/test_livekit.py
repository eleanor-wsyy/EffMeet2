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
            self.assertRegex(args[2], r'^[a-z][a-z0-9_]{0,63}$')
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

    def test_token_endpoint_decouples_participant_from_relay(self):
        from fastapi.testclient import TestClient
        from services.controller.app import create_app
        from services.controller.contracts import DemoError
        env = {'LIVEKIT_API_KEY': 'test', 'LIVEKIT_API_SECRET': 'a'*32,
               'LIVEKIT_URL': 'ws://127.0.0.1:7880'}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, env, clear=True):
            app = create_app(db_path=Path(tmp)/'test.sqlite3')
            with TestClient(app) as client:
                profiles = client.get('/api/demo/session').json()['profiles']
                headers = {'Authorization': 'Bearer '+profiles[1]['token']}
                mid = client.post('/api/v1/meetings', json={'title':'test'},
                                  headers={'Authorization':'Bearer '+profiles[0]['token']}).json()['meeting_id']
                app.state.livekit_bridge.join = AsyncMock(
                    side_effect=DemoError(503, 'ASR_NOT_CONFIGURED', 'no asr'))
                response = client.post(f'/api/v1/meetings/{mid}/livekit-token',
                                       json={'identity':'remote_1'}, headers=headers)
                self.assertEqual(response.status_code, 201)
                body = response.json()
                self.assertTrue(body['token'])
                self.assertEqual(body['room'], mid)
                self.assertFalse(body['relay_ready'])
                self.assertTrue(body['relay_pending'])

    def test_host_token_is_subscribe_only_and_operator_only(self):
        import jwt
        from fastapi.testclient import TestClient
        from services.controller.app import create_app
        env = {'LIVEKIT_API_KEY': 'test', 'LIVEKIT_API_SECRET': 'a'*32,
               'LIVEKIT_URL': 'ws://127.0.0.1:7880'}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, env, clear=True):
            with TestClient(create_app(db_path=Path(tmp)/'host.sqlite3')) as client:
                profiles = client.get('/api/demo/session').json()['profiles']
                operator = {'Authorization': 'Bearer '+profiles[0]['token']}
                remote = {'Authorization': 'Bearer '+profiles[1]['token']}
                mid = client.post('/api/v1/meetings', json={'title':'host'},
                                  headers=operator).json()['meeting_id']
                path = f'/api/v1/meetings/{mid}/livekit-host-token'
                self.assertEqual(client.post(path, headers=remote).status_code, 403)
                response = client.post(path, headers=operator)
                self.assertEqual(response.status_code, 201)
                body = response.json()
                self.assertEqual(body['room'], mid)
                claims = jwt.decode(body['token'], 'a'*32, algorithms=['HS256'])
                self.assertFalse(claims['video']['canPublish'])
                self.assertTrue(claims['video']['canSubscribe'])
                self.assertEqual(claims['video']['room'], mid)

    def test_csp_allows_only_the_configured_livekit_origin(self):
        from fastapi.testclient import TestClient
        from services.controller.app import create_app
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                with TestClient(create_app(db_path=Path(tmp)/'a.sqlite3')) as client:
                    csp = client.get('/healthz').headers['content-security-policy']
                    self.assertIn("connect-src 'self';", csp)
            with patch.dict(os.environ, {'LIVEKIT_URL':'wss://livekit.example.test'}, clear=True):
                with TestClient(create_app(db_path=Path(tmp)/'b.sqlite3')) as client:
                    csp = client.get('/healthz').headers['content-security-policy']
                    self.assertIn("connect-src 'self' wss://livekit.example.test "
                                  "https://livekit.example.test;", csp)
                    self.assertNotIn('livekit.example.test', client.get('/healthz').text)
            with patch.dict(os.environ, {'LIVEKIT_URL':'wss://host.test; script-src evil'}, clear=True):
                with TestClient(create_app(db_path=Path(tmp)/'c.sqlite3')) as client:
                    csp = client.get('/healthz').headers['content-security-policy']
                    self.assertIn("connect-src 'self';", csp)
                    self.assertNotIn('script-src evil', csp)
