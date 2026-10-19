export const MEDIA_PHASES = Object.freeze({
  idle: 'idle',
  connecting: 'connecting',
  connected: 'connected',
  muted: 'muted',
  live: 'live',
  reconnecting: 'reconnecting',
  closed: 'closed',
  error: 'error'
});

export function createMediaSession({Room, RoomEvent, onState = () => {}, roomOptions = {}} = {}) {
  if (typeof Room !== 'function') throw new TypeError('Room constructor is required');
  if (!RoomEvent || typeof RoomEvent !== 'object') throw new TypeError('RoomEvent is required');
  let room = null;
  let phase = MEDIA_PHASES.idle;
  let micOn = false;
  let intentionalClose = false;

  const emit = (next, detail = '') => {
    phase = next;
    onState({phase, detail, micOn});
  };

  async function connect({url, token} = {}) {
    if (!url || !token) {
      throw Object.assign(new Error('缺少媒体房间地址或凭据。'), {code: 'MEDIA_CREDENTIALS_MISSING'});
    }
    await disconnect({silent: true});
    intentionalClose = false;
    emit(MEDIA_PHASES.connecting);
    const next = new Room(roomOptions);
    room = next;
    next.on(RoomEvent.Disconnected, () => {
      if (room !== next) return;
      room = null;
      micOn = false;
      emit(MEDIA_PHASES.closed, intentionalClose ? '' : '音频房间连接已断开。');
    });
    next.on(RoomEvent.Reconnecting, () => {
      if (room === next) emit(MEDIA_PHASES.reconnecting);
    });
    next.on(RoomEvent.Reconnected, () => {
      if (room === next) emit(micOn ? MEDIA_PHASES.live : MEDIA_PHASES.connected);
    });
    try {
      await next.connect(url, token);
      if (room !== next) {
        await next.disconnect().catch(() => {});
        return;
      }
      emit(MEDIA_PHASES.connected);
    } catch (error) {
      if (room !== next) {
        await next.disconnect().catch(() => {});
        return;
      }
      room = null;
      micOn = false;
      await next.disconnect().catch(() => {});
      emit(MEDIA_PHASES.error, '音频服务器连接失败。');
      throw error;
    }
  }

  async function setMic(enabled) {
    if (!room) throw Object.assign(new Error('音频尚未连接。'), {code: 'MEDIA_NOT_CONNECTED'});
    const next = Boolean(enabled);
    try {
      await room.localParticipant.setMicrophoneEnabled(next);
      micOn = next && room.localParticipant.isMicrophoneEnabled !== false;
      emit(micOn ? MEDIA_PHASES.live : MEDIA_PHASES.muted);
      return micOn;
    } catch (error) {
      emit(MEDIA_PHASES.error, next ? '无法打开麦克风，请检查浏览器权限。' : '无法关闭麦克风。');
      throw error;
    }
  }

  async function disconnect({silent = false} = {}) {
    const current = room;
    room = null;
    micOn = false;
    if (!current) {
      if (!silent) emit(MEDIA_PHASES.closed);
      return;
    }
    intentionalClose = true;
    await current.disconnect().catch(() => {});
    if (!silent) emit(MEDIA_PHASES.closed);
  }

  return {
    connect,
    setMic,
    disconnect,
    get phase() { return phase; },
    get connected() { return Boolean(room); },
    get micOn() { return micOn; }
  };
}
