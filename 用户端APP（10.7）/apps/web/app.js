import {parseMeetingId, remainingSeconds, receiptState, effectiveState, shouldAutoOpen, candidateKey, candidateLabels, viewpointLabels, swipeTarget, candidateActions} from './state.js';

const $ = id => document.getElementById(id);
const model = {view:'join', mid:'', actor:'', nickname:'', token:'', snapshot:null, map:null, seen:new Set(), sheetId:null, busy:false, online:false, health:null, generation:0, timer:null, serverTime:0, observedAt:0, captureId:null, captureUrl:null, suppressNextAuto:false, polling:false, joining:false, decisionVersion:0, mapRevision:null, pendingSignature:"", opinionsSignature:"", mapSignature:""};
let focusBeforeSheet = null, closeTimer = null, toastTimer = null, mapFlight = null;
const serverNow = () => model.serverTime + (performance.now() - model.observedAt) / 1000;
const meetingPath = suffix => '/api/v1/meetings/' + encodeURIComponent(model.mid) + suffix;
const sessionStorageKey = () => 'effmeet2.seen.' + model.mid + '.' + model.actor;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function message(id, text = '') { $(id).textContent = text; $(id).hidden = !text; }
function toast(text) { clearTimeout(toastTimer); message('toast', text); toastTimer = setTimeout(() => message('toast'), 4200); }
async function request(url, {method='GET', body, auth=true, blob=false} = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  const headers = {};
  if (auth && model.token) headers.Authorization = 'Bearer ' + model.token;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  try {
    const response = await fetch(url, {method, headers, signal:controller.signal, cache:'no-store', body:body === undefined ? undefined : JSON.stringify(body)});
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw Object.assign(new Error(payload.error?.message || '请求失败，请稍后重试。'), {code:payload.error?.code, status:response.status});
    }
    return blob ? response.blob() : response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('连接超时，请检查本机服务。');
    throw error;
  } finally { clearTimeout(timeout); }
}
function markSeen(row) {
  model.seen.add(candidateKey(row));
  try { sessionStorage.setItem(sessionStorageKey(), JSON.stringify([...model.seen])); } catch { /* Storage can be unavailable in private mode. */ }
}
function ownCandidates() { return (model.snapshot?.interventions || []).filter(r => r.candidate.owner_speaker_id === model.actor); }
function showView(view) {
  if (model.sheetId) closeSheet();
  model.view = view;
  for (const name of ['join', 'live', 'map']) $('view-' + name).hidden = name !== view;
  if (view !== 'live') for (const row of ownCandidates()) markSeen(row);
  if (view === 'map') { renderMap(); refreshMap(true); }
  const title = view === 'live' ? $('lv-title') : $(view === 'map' ? 'map-title' : 'join-title');
  title.tabIndex = -1; title.focus({preventScroll:true});
}
async function authorizeMic() {
  const button = $('j-mic'); button.disabled = true;
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('当前浏览器不能访问麦克风，请使用 localhost 或 HTTPS。');
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    stream.getTracks().forEach(track => track.stop()); // Permission check only, no fake live microphone.
    $('mic-permission-status').textContent = '麦克风已授权；本次检查已停止收音。音频传输需另外接通。';
    $('j-mic-label').textContent = '重新检查麦克风';
  } catch (error) {
    $('mic-permission-status').textContent = error.name === 'NotAllowedError' ? '麦克风未获授权。仍可浏览会议，暂时不能发言。' : error.message;
  } finally { button.disabled = false; }
}
function updateJoinAvailability() {
  let valid = false;
  try { valid = Boolean(parseMeetingId($('j-mid').value)) && Boolean($('j-name').value.trim()); } catch { /* Keep incomplete forms disabled. */ }
  $('j-submit').disabled = model.joining || !valid;
}
async function join(event) {
  event.preventDefault(); if (model.joining) return; message('j-err');
  model.joining = true; updateJoinAvailability(); $('j-submit-label').textContent = '正在连接…';
  const generation = ++model.generation;
  try {
    const mid = parseMeetingId($('j-mid').value);
    const nickname = $('j-name').value.trim();
    if (!nickname) throw new Error('请填写你在会议中的名字。');
    const [session, health] = await Promise.all([request('/api/demo/session',{auth:false}), request('/healthz',{auth:false})]);
    if (generation !== model.generation) return;
    const actor = $('j-identity').value;
    const profile = session.profiles.find(p => p.actor === actor && ['remote_1','remote_2'].includes(p.actor));
    if (!profile) throw new Error('此联调身份不可用，请重新选择。');
    model.mid = mid; model.nickname = nickname; model.actor = actor; model.token = profile.token; model.health = health;
    const snapshot = await request('/api/demo/meetings/' + encodeURIComponent(mid) + '/state');
    if (generation !== model.generation) return;
    model.seen = new Set();
    try { const stored = JSON.parse(sessionStorage.getItem(sessionStorageKey()) || '[]'); if (Array.isArray(stored)) model.seen = new Set(stored); } catch { /* Memory-only suppression if storage is unavailable. */ }
    model.map = null; model.mapRevision = null; model.suppressNextAuto = false;
    model.pendingSignature = model.opinionsSignature = model.mapSignature = '';
    receiveSnapshot(snapshot); showView('live'); updateEnvironment(health); startPolling();
  } catch (error) { if (generation === model.generation) { model.token = ''; message('j-err', error.message); } }
  finally { if (generation === model.generation) { model.joining = false; updateJoinAvailability(); $('j-submit-label').textContent = '进入会议'; } }
}
function updateEnvironment(health) {
  $('environment').textContent = health.mode === 'bench' ? '本机台架 · 硬件和音频能力以实际配置为准' : '本机模拟 · 已接真实控制器，机器人回执为模拟数据';
}
async function refreshMap(force = false) {
  if (!model.mid || !model.snapshot) return;
  const generation = model.generation, revision = model.snapshot.viewpoint_revision;
  if (!force && model.map && revision === model.mapRevision) return;
  if (mapFlight?.generation === generation) return mapFlight.promise;
  const work = (async () => {
    try {
      const map = await request(meetingPath('/viewpoint-map'));
      if (generation !== model.generation) return;
      model.map = map; model.mapRevision = revision;
      renderOpinions(); renderMap(); message('map-error');
    } catch (error) { if (generation === model.generation) message('map-error', error.message); }
    finally { if (mapFlight?.generation === generation) mapFlight = null; }
  })();
  mapFlight = {generation, promise:work}; return work;
}
function receiveSnapshot(snapshot) {
  model.snapshot = snapshot; model.serverTime = snapshot.server_time; model.observedAt = performance.now(); model.online = true;
  $('lv-title').textContent = snapshot.title;
  $('session-name').textContent = model.nickname;
  $('connection-state').textContent = snapshot.mode === 'bench' ? '本机台架已连接' : '本机模拟已连接';
  // The controller does not expose a live capture session. Never label a permission check as recording.
  const recording = model.health?.audio_capture === true;
  $('lv-status').textContent = recording ? '录音中' : '会议进行中'; $('recording-dot').hidden = !recording;
  const latest = snapshot.utterances.at(-1);
  $('lv-speaker').textContent = latest ? speakerName(latest.speaker_id) : '现场';
  $('lv-transcript').textContent = latest?.text || '等待发言…';
  message('live-error'); renderPending(); renderOpinions(); renderSheet();
}
async function pollOnce(generation) {
  const decisionVersion = model.decisionVersion;
  try {
    const snapshot = await request('/api/demo/meetings/' + encodeURIComponent(model.mid) + '/state');
    if (generation !== model.generation || decisionVersion !== model.decisionVersion) return;
    receiveSnapshot(snapshot);
    if (document.hidden || model.view !== 'live' || model.suppressNextAuto) {
      for (const row of ownCandidates()) markSeen(row);
      model.suppressNextAuto = false;
    } else if (!model.sheetId && !model.busy) {
      const row = ownCandidates().find(r => shouldAutoOpen(r, {actor:model.actor, visible:!document.hidden, live:model.view === 'live', seen:model.seen, serverNow:serverNow()}));
      if (row) openSheet(row);
    }
    await Promise.all([refreshMap(), refreshCapture(generation)]);
  } catch (error) {
    if (generation !== model.generation) return;
    model.online = false; $('connection-state').textContent = '连接中断';
    message('live-error', error.status === 401 ? '调试会话已失效，请离开后重新入会。' : error.message);
    renderSheet(); renderPending();
  }
}
function startPolling() {
  if (model.polling || !model.mid) return;
  clearTimeout(model.timer); const generation = model.generation;
  const tick = async () => {
    if (generation !== model.generation) return;
    model.polling = true;
    try { if (!document.hidden) await pollOnce(generation); }
    finally {
      if (generation === model.generation) { model.polling = false; model.timer = setTimeout(tick, 2000); }
    }
  };
  tick();
}
function speakerName(id) {
  if (id === model.actor) return model.nickname + ' · 线上';
  if (id === 'remote_1') return '线上成员 1';
  if (id === 'remote_2') return '线上成员 2';
  return id ? id + ' · 现场' : '未知发言者';
}
function renderPending() {
  const rows = ownCandidates().slice().reverse();
  const signature = JSON.stringify(rows.map(r => [r.candidate, effectiveState(r,model.snapshot.commands,serverNow())]));
  if (signature === model.pendingSignature) return; model.pendingSignature = signature;
  $('pending-section').hidden = !rows.length;
  $('pending-count').textContent = rows.filter(r => effectiveState(r, model.snapshot.commands, serverNow()) === 'awaiting_confirmation').length + ' 条待决定';
  $('pending-list').replaceChildren(...rows.map(row => {
    const card = node('article','card pending-card');
    card.append(node('h3','', '你的观点可能还没被现场听到'), node('p','',row.candidate.proposed_text));
    const bottom = node('div','pending-bottom');
    const state = effectiveState(row, model.snapshot.commands, serverNow());
    const status = node('span','', candidateLabels[state] || state); status.dataset.candidateStatus = row.candidate.intervention_id;
    const button = node('button','','查看状态');
    button.type = 'button'; button.dataset.candidate = row.candidate.intervention_id; button.addEventListener('click',() => openSheet(row));
    bottom.append(status,button); card.append(bottom); return card;
  }));
}
function opinionCard(viewpoint, isMap) {
  const card = node('article','card opinion-card' + (isMap ? ' map-card' : ''));
  const head = node('div','opinion-head');
  const state = viewpoint.response_status;
  head.append(node('strong','',speakerName(viewpoint.speaker_id)));
  const tag = node('span','tag ' + (state === 'responded' ? 'ok' : ['uncertain','possibly_unresponded'].includes(state) ? 'warn' : ''), viewpointLabels[state] || '尚未核对');
  if (!isMap) head.append(tag);
  card.append(head); if (isMap) card.append(tag);
  card.append(node('p','opinion-text',viewpoint.text));
  const evidence = model.snapshot?.utterances || [];
  const responses = evidence.filter(u => viewpoint.response_evidence_ids?.includes(u.utterance_id));
  if (responses.length) card.append(node('p','reply', responses.map(u => speakerName(u.speaker_id) + '：' + u.text).join('\n')));
  if (state === 'uncertain') card.append(node('p','reply','这条关系不确定，请会后核对'));
  if (isMap) {
    const details = node('details'); details.append(node('summary','', '查看原话'));
    const original = evidence.filter(u => viewpoint.evidence_ids?.includes(u.utterance_id));
    for (const u of original) details.append(node('p','',speakerName(u.speaker_id) + '：' + u.text));
    if (!original.length) details.append(node('p','', '原话证据暂不可用，请刷新后核对。'));
    card.append(details);
  }
  return card;
}
function renderOpinions() {
  const views = model.map?.viewpoints?.filter(v => v.speaker_id === model.actor) || (model.snapshot?.utterances || []).filter(u => u.speaker_id === model.actor).map(u => ({speaker_id:u.speaker_id, text:u.text, response_status:'no_analysis', evidence_ids:[u.utterance_id]}));
  const signature = JSON.stringify([views,model.snapshot?.utterances]);
  if (signature === model.opinionsSignature) return; model.opinionsSignature = signature;
  $('lv-count').textContent = views.length + ' 条';
  $('lv-ops').replaceChildren(...(views.length ? views.map(v => opinionCard(v,false)) : [node('p','empty-state','你的发言会保留在这里，提醒前始终由你决定。')]));
}
function renderMap() {
  const views = model.map?.viewpoints || [];
  const signature = JSON.stringify([model.map ? views : null,model.snapshot?.utterances]);
  if (signature === model.mapSignature) return; model.mapSignature = signature;
  $('stat-all').textContent = views.length;
  $('stat-responded').textContent = views.filter(v => v.response_status === 'responded').length;
  $('stat-review').textContent = views.filter(v => v.response_status !== 'responded').length;
  $('map-list').replaceChildren(...(views.length ? views.map(v => opinionCard(v,true)) : [node('p','empty-state',model.map ? '尚无观点记录，等待会议发言。' : '正在读取观点地图…')]));
}
async function refreshCapture(generation) {
  try {
    const captures = await request(meetingPath('/captures'));
    if (generation !== model.generation) return;
    const latest = captures.at(-1);
    if (!latest || latest.capture_id === model.captureId) return;
    const asset = await request(meetingPath('/captures/' + encodeURIComponent(latest.capture_id)),{blob:true});
    if (generation !== model.generation) return;
    const next = URL.createObjectURL(asset); const previous = model.captureUrl;
    model.captureId = latest.capture_id; model.captureUrl = next;
    $('lv-img').src = next; $('lv-img').hidden = false; $('capture-empty').hidden = true;
    $('lv-viewimg').href = next; $('lv-viewimg').hidden = false;
    if (previous) URL.revokeObjectURL(previous);
  } catch { /* Keep the last original image rather than substituting fabricated imagery. */ }
}
function openSheet(row) {
  row = ownCandidates().find(r => candidateKey(r) === candidateKey(row));
  if (!row || model.view !== 'live' || document.hidden) return;
  clearTimeout(closeTimer); model.sheetId = candidateKey(row); markSeen(row);
  focusBeforeSheet = document.activeElement; message('sh-error'); renderSheet();
  $('screens').inert = true; $('overlay').hidden = false;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!model.sheetId) return; $('overlay').classList.add('open'); $('sheet').focus({preventScroll:true});
  }));
}
function closeSheet() {
  model.sheetId = null; $('overlay').classList.remove('open');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  clearTimeout(closeTimer); closeTimer = setTimeout(() => {
    if (model.sheetId) return; $('overlay').hidden = true; $('screens').inert = false;
    if (focusBeforeSheet?.isConnected && model.view === 'live') focusBeforeSheet.focus({preventScroll:true});
  },reduced ? 0 : 280);
}
function renderSheet() {
  if (!model.sheetId) return;
  const row = ownCandidates().find(r => candidateKey(r) === model.sheetId);
  if (!row) { closeSheet(); return; }
  const actions = candidateActions(row, model.snapshot.commands, serverNow());
  const state = actions.state;
  const seconds = remainingSeconds(row,serverNow());
  $('sh-quote').textContent = row.candidate.proposed_text;
  $('sh-meta').textContent = '你说的 · 原话证据 ' + row.candidate.evidence_ids.length + ' 条';
  $('sh-state').textContent = candidateLabels[state] || state;
  $('sh-countdown').textContent = state === 'awaiting_confirmation' ? (seconds === null ? '截止时间暂不可用，请刷新后再决定。' : seconds + ' 秒内有效') : state === 'expired' ? '有效期已结束。点击「请机器人提醒」后会重新校验，仍满足条件才提交提醒。' : model.snapshot.mode === 'mock' ? '本机模拟回执，不代表真实机器人已播报。' : '';
  $('sh-actions').hidden = false;
  $('sh-confirm').disabled = model.busy || !model.online || !actions.confirmMode;
  $('sh-confirm').textContent = model.busy ? '正在提交…' : '请机器人提醒';
  $('sh-dismiss').hidden = !actions.canDismiss;
  $('sh-actions').classList.toggle('single', !actions.canDismiss);
  $('sh-dismiss').disabled = model.busy || !model.online || !actions.canDismiss;
}
async function decide(decision) {
  if (model.busy || !model.online || !model.sheetId) return;
  let row = ownCandidates().find(r => candidateKey(r) === model.sheetId);
  if (!row) return;
  const actions = candidateActions(row, model.snapshot.commands, serverNow());
  if (decision === 'confirm' ? !actions.confirmMode : !actions.canDismiss) return;
  const id = candidateKey(row), generation = model.generation;
  model.busy = true; message('sh-error'); renderSheet();
  try {
    if (decision === 'confirm' && actions.confirmMode === 'recheck') {
      const renewed = await request(meetingPath('/interventions/' + encodeURIComponent(id) + '/recheck'), {method:'POST',body:{expected_revision:row.state_revision}});
      if (generation !== model.generation) return;
      // Keep it in this dialog; never auto-extend a deadline on open or poll.
      model.decisionVersion++;
      Object.assign(row, renewed);
      renderPending(); renderSheet();
    }
    const result = await request(meetingPath('/interventions/' + encodeURIComponent(id) + '/decision'),{method:'POST',body:{decision,expected_revision:row.state_revision}});
    if (generation !== model.generation) return;
    // Use response receipts immediately. Mock can be completed in one transaction; do not invent a wait animation.
    model.decisionVersion++;
    const current = ownCandidates().find(r => candidateKey(r) === id);
    if (current) {
      current.decision = decision; current.state_revision = result.event?.payload?.state_revision ?? row.state_revision + 1;
      current.state = decision === 'dismiss' ? 'dismissed' : receiptState(result.receipts);
    }
    if (result.command) {
      model.snapshot.commands = model.snapshot.commands.filter(c => c.command.command_id !== result.command.command_id);
      model.snapshot.commands.push({command:result.command,receipts:result.receipts || []});
    }
    if (decision === 'dismiss') closeSheet();
    renderPending(); renderSheet();
    // Next serial poll reconciles revision / device state; no duplicate decision request.
  } catch (error) {
    if (generation !== model.generation) return;
    if (model.sheetId === id) message('sh-error',error.message); else toast(error.message);
    if (error.status === 409) {
      try { const snapshot = await request('/api/demo/meetings/' + encodeURIComponent(model.mid) + '/state'); if (generation === model.generation) receiveSnapshot(snapshot); } catch { model.online = false; }
    }
  } finally { if (generation === model.generation) { model.busy = false; renderSheet(); } }
}
async function exportMap() {
  const button = $('export-map'); button.disabled = true;
  try {
    const generation = model.generation;
    const [map,snapshot] = await Promise.all([request(meetingPath('/viewpoint-map')),request('/api/demo/meetings/' + encodeURIComponent(model.mid) + '/state')]);
    if (generation !== model.generation) return;
    const data = {format:'effmeet2-evidence-export-v1',exported_at:new Date().toISOString(),meeting_id:model.mid,title:snapshot.title,mode:snapshot.mode,viewpoint_map:map,utterances:snapshot.utterances,interventions:snapshot.interventions,commands:snapshot.commands,notice:'保留原话和可核对证据；AI 推测不是本人核对结果。'};
    const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}));
    const anchor = node('a'); anchor.href = url; anchor.download = 'EffMeet2-' + model.mid + '.json'; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url),1000); toast('已导出含原话证据的 JSON 会议记录');
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; }
}
function leave() {
  model.generation++; clearTimeout(model.timer); clearTimeout(closeTimer);
  model.sheetId = null; $('overlay').classList.remove('open'); $('overlay').hidden = true; $('screens').inert = false;
  model.token = ''; model.mid = ''; model.actor = ''; model.snapshot = null; model.map = null;
  model.busy = false; model.polling = false; model.captureId = null; model.mapRevision = null;
  if (model.captureUrl) URL.revokeObjectURL(model.captureUrl);
  model.captureUrl = null; $('lv-img').removeAttribute('src'); $('lv-img').hidden = true;
  $('capture-empty').hidden = false; $('lv-viewimg').hidden = true; $('lv-viewimg').removeAttribute('href');
  showView('join');
}
$('join-form').addEventListener('submit',join); $('j-mic').addEventListener('click',authorizeMic);
$('open-map').addEventListener('click',() => showView('map')); $('back-live').addEventListener('click',() => showView('live'));
$('leave-meeting').addEventListener('click',leave); $('refresh-state').addEventListener('click',() => { model.online = false; renderSheet(); startPolling(); });
$('export-map').addEventListener('click',exportMap);
$('live-mic').addEventListener('click',() => toast('音频传输尚未接通；麦克风授权不会开始录音或上传。'));
for (const id of ['j-mid','j-name']) $(id).addEventListener('input',updateJoinAvailability);
for (const id of ['scrim','sheet-close','sheet-handle']) $(id).addEventListener('click',closeSheet);
$('sh-confirm').addEventListener('click',() => decide('confirm')); $('sh-dismiss').addEventListener('click',() => decide('dismiss'));
document.addEventListener('visibilitychange',() => { if (document.hidden) { model.suppressNextAuto = true; if (model.sheetId) closeSheet(); } });
let swipeStart = null;
$('screens').addEventListener('pointerdown',e => { if (e.target.closest('button,a,input,select,summary,details') || model.view === 'join') return; swipeStart = {x:e.clientX,y:e.clientY}; });
$('screens').addEventListener('pointerup',e => {
  if (!swipeStart) return; const dx=e.clientX-swipeStart.x, dy=e.clientY-swipeStart.y; swipeStart=null;
  const target = swipeTarget(model.view, dx, dy);
  if (target) showView(target);
});
$('screens').addEventListener('pointercancel',() => {swipeStart=null;});
let dragY = null;
$('sheet-handle').addEventListener('pointerdown',e => {dragY=e.clientY; e.currentTarget.setPointerCapture(e.pointerId);});
$('sheet-handle').addEventListener('pointerup',e => {if(dragY!==null && e.clientY-dragY>50) closeSheet(); dragY=null;});
$('sheet-handle').addEventListener('pointercancel',() => {dragY=null;});
$('sheet').addEventListener('keydown',e => {
  if (e.key==='Escape') {e.preventDefault(); closeSheet(); return;}
  if (e.key!=='Tab') return;
  const focusable=[...$('sheet').querySelectorAll('button:not(:disabled),a[href]')].filter(n=>!n.closest('[hidden]'));
  const first=focusable[0], last=focusable.at(-1);
  if(e.shiftKey && (document.activeElement===first || document.activeElement===$('sheet'))) {e.preventDefault();last?.focus();}
  else if(!e.shiftKey && (document.activeElement===last || document.activeElement===$('sheet'))) {e.preventDefault();first?.focus();}
});
setInterval(() => {
  if (!model.snapshot || document.hidden) return;
  renderSheet(); renderPending();
},1000);
request('/healthz',{auth:false}).then(updateEnvironment).catch(()=>{$('environment').textContent='本机服务未连接，请先启动控制器。';});
const invite = new URL(location.href).searchParams.get('meeting_id'); if(invite) $('j-mid').value=invite;

// This PWA caches only its static shell; meeting evidence and decisions remain server-only.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/app/sw.js', {scope:'/app/'}).catch(() => {}));
}
window.addEventListener('offline', () => {
  if (!model.mid) return;
  model.online = false; $('connection-state').textContent = '连接中断';
  renderSheet(); renderPending();
});
window.addEventListener('online', () => {
  if (model.mid && !model.polling) startPolling();
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && model.mid && !model.polling) startPolling();
});
updateJoinAvailability();