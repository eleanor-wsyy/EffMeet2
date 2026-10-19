import {Room, RoomEvent, Track} from '/app/vendor/livekit-client.esm.mjs';

const button = document.getElementById('remote-audio');
const status = document.getElementById('remote-audio-status');
const sink = document.getElementById('remote-audio-sink');
let room = null;

const setStatus = text => { if (status) status.textContent = text; };
const meetingId = () => window.effmeetMeetingId || '';

async function operatorToken() {
  const response = await fetch('/api/demo/session', {cache:'no-store'});
  if (!response.ok) throw new Error('无法读取本机调试会话。');
  const payload = await response.json();
  const profile = payload.profiles?.find(item => item.actor === 'operator');
  if (!profile) throw new Error('本机调试会话没有主持人身份。');
  return profile.token;
}

async function connect() {
  const mid = meetingId();
  if (!mid) { setStatus('请先新建会议，再加入远程音频。'); return; }
  button.disabled = true;
  let stage = 'token';
  setStatus('正在加入远程音频…');
  try {
    const response = await fetch('/api/v1/meetings/' + encodeURIComponent(mid) + '/livekit-host-token', {
      method:'POST',
      headers:{Authorization:'Bearer ' + await operatorToken(), 'Content-Type':'application/json'},
      body:'{}'
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const code = payload.error?.code;
      throw Object.assign(new Error(code === 'LIVEKIT_NOT_CONFIGURED'
        ? '音频未配置：服务端需要 LIVEKIT_URL/API_KEY/SECRET。'
        : (payload.error?.message || '无法取得远程音频凭据。')), {code});
    }
    stage = 'connect';
    room = new Room({adaptiveStream:false, dynacast:false});
    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind !== Track.Kind.Audio) return;
      const element = track.attach();
      element.autoplay = true;
      element.playsInline = true;
      element.controls = true;
      element.style.width = '100%';
      element.style.maxWidth = '420px';
      sink?.append(element);
      element.play?.().catch(() => setStatus('已订阅远程音频；浏览器阻止了自动播放，请按播放器按钮。'));
    });
    room.on(RoomEvent.TrackUnsubscribed, track => {
      for (const element of track.detach()) element.remove();
    });
    room.on(RoomEvent.TrackMuted, (publication, participant) => {
      if (publication.kind === Track.Kind.Audio) setStatus(`${participant.identity} 已静音。`);
    });
    room.on(RoomEvent.TrackUnmuted, (publication, participant) => {
      if (publication.kind === Track.Kind.Audio) setStatus(`${participant.identity} 已取消静音。`);
    });
    room.on(RoomEvent.Reconnecting, () => setStatus('远程音频重连中…'));
    room.on(RoomEvent.Reconnected, () => setStatus('远程音频已恢复。'));
    room.on(RoomEvent.Disconnected, () => {
      room = null;
      button.textContent = '加入远程音频';
      button.disabled = false;
      setStatus('远程音频已断开。');
    });
    await room.connect(payload.url, payload.token);
    button.textContent = '离开远程音频';
    setStatus('已加入远程音频；远程成员发言会从本机扬声器播放。');
  } catch (error) {
    if (room) { await room.disconnect().catch(() => {}); room = null; }
    button.textContent = '加入远程音频';
    setStatus(error.code === 'LIVEKIT_NOT_CONFIGURED' || stage === 'token'
      ? (error.message || '无法取得远程音频凭据。')
      : '远程音频连接失败。');
  } finally {
    button.disabled = false;
  }
}

async function disconnect() {
  if (!room) return;
  button.disabled = true;
  const current = room;
  room = null;
  await current.disconnect().catch(() => {});
  button.textContent = '加入远程音频';
  button.disabled = false;
  setStatus('远程音频已断开。');
}

button?.addEventListener('click', () => room ? disconnect() : connect());
window.addEventListener('beforeunload', () => { room?.disconnect().catch(() => {}); });
