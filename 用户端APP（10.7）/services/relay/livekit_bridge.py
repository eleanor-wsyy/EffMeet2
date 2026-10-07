"""One subscribed room per meeting; bounded offline ASR segments, no recording."""
import asyncio
import logging
import struct
import time
from uuid import uuid4, uuid5, NAMESPACE_URL
from .livekit_token import issue_token
from services.controller.contracts import DemoError

log = logging.getLogger(__name__)


class RemoteIngest:
    def __init__(self, store, asr):
        self.store, self.asr = store, asr
        self.asr_lock = asyncio.Lock()

    async def ingest(self, meeting, speaker, stream, segment, pcm, start_ms):
        if speaker not in {'remote_1', 'remote_2'}:
            raise ValueError('UNBOUND_REMOTE_IDENTITY')
        if not pcm or len(pcm) % 2 or len(pcm) > 960000:
            raise ValueError('INVALID_REMOTE_PCM')
        async with self.asr_lock:
            text = await self.asr.transcribe(pcm, segment)
        if not text:
            return None
        return self.store.add_utterance(meeting, {
            'utterance_id': str(uuid5(NAMESPACE_URL, 'livekit:' + segment)),
            'stream_id': stream, 'speaker_id': speaker, 'channel': 'remote',
            'start_ms': start_ms, 'end_ms': start_ms + len(pcm) // 32,
            'text': text, 'final': True, 'revision': 1},
            mode=self.asr.mode, source='livekit_remote_asr', producer='asr')


class LiveKitBridge:
    def __init__(self, store, asr):
        self.ingest = RemoteIngest(store, asr)
        self.rooms, self.tasks = {}, {}
        self.lock = asyncio.Lock()
        self.epochs, self.errors = {}, {}

    async def join(self, meeting):
        if self.ingest.asr is None:
            raise DemoError(503, 'ASR_NOT_CONFIGURED', '远程音轨需要 ASR。')
        from livekit import rtc
        async with self.lock:
            if meeting in self.rooms:
                if self.rooms[meeting].isconnected():
                    return
                raise DemoError(503, 'LIVEKIT_RECONNECTING', 'relay 正在重连，请重试。')
            room = rtc.Room()
            self.epochs.setdefault(meeting, time.monotonic())
            @room.on('track_subscribed')
            def subscribed(track, publication, participant):
                if (track.kind != rtc.TrackKind.KIND_AUDIO or
                        publication.source != rtc.TrackSource.SOURCE_MICROPHONE or
                        participant.identity not in {'remote_1', 'remote_2'}):
                    return
                key = (meeting, participant.identity)
                if key in self.tasks and not self.tasks[key].done():
                    self.tasks[key].cancel()
                self.tasks[key] = asyncio.create_task(
                    self.consume(meeting, participant.identity, track))
            @room.on('disconnected')
            def disconnected(*_):
                if self.rooms.get(meeting) is room:
                    self.rooms.pop(meeting, None)
                for key, task in list(self.tasks.items()):
                    if key[0] == meeting:
                        task.cancel()
            credentials = issue_token(meeting, 'effmeet-relay-' + meeting, relay=True)
            try:
                await asyncio.wait_for(room.connect(credentials['url'], credentials['token']), 15)
            except Exception:
                await room.disconnect()
                raise DemoError(502, 'LIVEKIT_CONNECT_FAILED', 'relay 连接失败，检查服务配置。')
            self.rooms[meeting] = room

    async def consume(self, meeting, speaker, track):
        from livekit import rtc
        stream_id = 'lk-' + str(uuid4())
        stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1, capacity=50)
        queue = asyncio.Queue(maxsize=4)
        async def worker():
            while True:
                item = await queue.get()
                try:
                    if item is None:
                        return
                    segment, pcm, start = item
                    await self.ingest.ingest(meeting, speaker, stream_id, segment, pcm, start)
                except Exception:
                    self.errors[meeting] = 'REMOTE_ASR_FAILED'
                    log.exception('Remote ASR segment failed for meeting %s', meeting)
                finally:
                    queue.task_done()
        task = asyncio.create_task(worker())
        pcm, samples, start, quiet = bytearray(), 0, 0, 0
        offset_ms = int((time.monotonic() - self.epochs[meeting]) * 1000)
        def flush():
            nonlocal pcm, quiet
            if pcm:
                # Backpressure failure is observable; never grow memory without bound.
                queue.put_nowait((str(uuid4()), bytes(pcm), start))
            pcm, quiet = bytearray(), 0
        try:
            async for event in stream:
                data = bytes(event.frame.data)
                active = any(abs(v[0]) > 500 for v in struct.iter_unpack('<h', data))
                if active or pcm:
                    if not pcm:
                        start = offset_ms + samples // 16
                    pcm.extend(data)
                    quiet = 0 if active else quiet + len(data) // 2
                    if quiet >= 12800 or len(pcm) >= 160000:
                        flush()
                samples += len(data) // 2
            flush()
            await queue.join()
        except asyncio.CancelledError:
            raise
        except Exception:
            self.errors[meeting] = 'REMOTE_STREAM_FAILED'
            log.exception('Remote audio stream failed for meeting %s', meeting)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await stream.aclose()

    async def close(self):
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        for room in list(self.rooms.values()):
            await room.disconnect()
        self.rooms.clear()
