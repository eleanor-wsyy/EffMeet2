import test from 'node:test';
import assert from 'node:assert/strict';
import {createMediaSession, MEDIA_PHASES} from '../media.js';

const RoomEvent = {Disconnected:'disconnected', Reconnecting:'reconnecting', Reconnected:'reconnected'};
let lastRoom;

class FakeRoom {
  constructor() {
    lastRoom = this;
    this.handlers = new Map();
    this.connectedWith = null;
    this.disconnects = 0;
    this.localParticipant = {
      isMicrophoneEnabled: false,
      micCalls: [],
      async setMicrophoneEnabled(value) {
        this.micCalls.push(value);
        this.isMicrophoneEnabled = value;
      }
    };
  }
  on(event, handler) { this.handlers.set(event, handler); }
  emit(event) { this.handlers.get(event)?.(); }
  async connect(url, token) { this.connectedWith = {url, token}; }
  async disconnect() { this.disconnects++; }
}

function session(overrides = {}) {
  const states = [];
  const media = createMediaSession({Room:FakeRoom, RoomEvent, onState:state => states.push(state), ...overrides});
  return {media, states};
}

test('connect uses the short-lived token and reports connected', async () => {
  const {media, states} = session();
  await media.connect({url:'ws://livekit.test', token:'short-lived'});
  assert.equal(lastRoom.connectedWith.url, 'ws://livekit.test');
  assert.equal(lastRoom.connectedWith.token, 'short-lived');
  assert.equal(media.connected, true);
  assert.deepEqual(states.map(s => s.phase), [MEDIA_PHASES.connecting, MEDIA_PHASES.connected]);
});

test('microphone publishes only after the user enables it', async () => {
  const {media, states} = session();
  await media.connect({url:'ws://livekit.test', token:'t'});
  assert.equal(media.micOn, false);
  assert.equal(lastRoom.localParticipant.micCalls.length, 0);
  await media.setMic(true);
  assert.equal(media.micOn, true);
  assert.deepEqual(lastRoom.localParticipant.micCalls, [true]);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.live);
  await media.setMic(false);
  assert.equal(media.micOn, false);
  assert.deepEqual(lastRoom.localParticipant.micCalls, [true, false]);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.muted);
});

test('disconnect stops the room and clears microphone state', async () => {
  const {media, states} = session();
  await media.connect({url:'ws://livekit.test', token:'t'});
  await media.setMic(true);
  await media.disconnect();
  assert.equal(lastRoom.disconnects, 1);
  assert.equal(media.connected, false);
  assert.equal(media.micOn, false);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.closed);
});

test('room disconnect event is reflected without claiming audio is live', async () => {
  const {media, states} = session();
  await media.connect({url:'ws://livekit.test', token:'t'});
  await media.setMic(true);
  lastRoom.emit(RoomEvent.Disconnected);
  assert.equal(media.connected, false);
  assert.equal(media.micOn, false);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.closed);
  assert.match(states.at(-1).detail, /断开/);
});

test('reconnecting and reconnected preserve the chosen microphone state', async () => {
  const {media, states} = session();
  await media.connect({url:'ws://livekit.test', token:'t'});
  await media.setMic(true);
  lastRoom.emit(RoomEvent.Reconnecting);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.reconnecting);
  lastRoom.emit(RoomEvent.Reconnected);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.live);
});

test('missing credentials fail before creating a room', async () => {
  const {media} = session();
  await assert.rejects(() => media.connect({url:'ws://livekit.test'}), error => error.code === 'MEDIA_CREDENTIALS_MISSING');
  assert.equal(media.connected, false);
});

test('connect failure reports an error and does not leave a connected room', async () => {
  class FailingRoom extends FakeRoom {
    async connect() { throw new Error('server unavailable'); }
  }
  const states = [];
  const media = createMediaSession({Room:FailingRoom, RoomEvent, onState:state => states.push(state)});
  await assert.rejects(() => media.connect({url:'ws://livekit.test', token:'t'}), /server unavailable/);
  assert.equal(media.connected, false);
  assert.equal(states.at(-1).phase, MEDIA_PHASES.error);
});

test('microphone cannot be enabled before the room connects', async () => {
  const {media} = session();
  await assert.rejects(() => media.setMic(true), error => error.code === 'MEDIA_NOT_CONNECTED');
});
