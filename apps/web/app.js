import { parseMeetingId, candidateLabels } from './state.js';
import {
  loadDB, persist, resetDB, remainingMinutes, PLANS, setPlan,
  activeMeeting as buildActiveMeeting, endActiveMeeting, findMeeting,
  updateTodo, addScheduled, removeScheduled, speakerOf, viewpointStateLabel
} from './store.js';

const $ = id => document.getElementById(id);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const MAIN_PAGES = ['home', 'meeting', 'history', 'profile'];
const pad = value => String(value).padStart(2, '0');

let db = loadDB();
let currentPage = 'home';
let joinReturn = 'home';
let scheduleReturn = 'home';
let detailMeeting = null;
let detailTab = 'minutes';
let detailReturn = 'history';
let historyQuery = '';
let historyFilter = 'all';
let joinBusy = false;
let joinCameraGranted = false;
let autoPromptOpened = false;
let autoPromptTimer = null;
let promptOpen = false;
let lastPromptState = '';
let promptBusy = false;
let dialogHandler = null;
let dialogCloseTimer = null;
let promptCloseTimer = null;
let toastTimer = null;
let promptTimers = [];
let reconnecting = false;
let stageId = null;
let selfCameraOn = false;
let selfCameraStream = null;
let meetingMicMuted = false;
let scanStream = null;
let scanTimer = null;
let scanBusy = false;

/* ---------- 通用 ---------- */
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function toast(text) {
  clearTimeout(toastTimer);
  const element = $('toast');
  element.textContent = text;
  element.hidden = false;
  toastTimer = setTimeout(() => { element.hidden = true; }, 3200);
}

function clearPromptTimers() {
  promptTimers.forEach(timer => clearTimeout(timer));
  promptTimers = [];
}

function promptState(prompt) {
  if (!prompt) return null;
  if (prompt.state === 'awaiting_confirmation' && prompt.expiresAt <= Date.now()) return 'expired';
  return prompt.state;
}

function promptLabel(state) {
  return candidateLabels[state] || state || '等待你的决定';
}

function remainingSeconds(prompt) {
  if (!prompt?.expiresAt) return 0;
  return Math.max(0, Math.ceil((prompt.expiresAt - Date.now()) / 1000));
}

/* ---------- 日期与格式 ---------- */
function timeOf(iso) {
  const date = new Date(iso);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function dayLabel(iso) {
  const date = new Date(iso);
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.round((start - target) / 86400000);
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function fullDate(iso) {
  const date = new Date(iso);
  return `${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function resetLabel(iso) {
  const date = new Date(`${iso}T00:00:00`);
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日重置`;
}

function elapsedLabel(startedAt) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000));
  return `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`;
}

function localDateInput(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function scheduleLabel(schedule) {
  const target = new Date(`${schedule.date}T${schedule.time}:00`);
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  const diff = Math.round((day - start) / 86400000);
  const prefix = diff === 0 ? '今天' : diff === 1 ? '明天' : `${target.getMonth() + 1}月${target.getDate()}日`;
  return `${prefix} ${schedule.time}`;
}

function initials(name) {
  return String(name || '?').trim().slice(0, 1) || '?';
}

function avatar(speaker, size = 'avatar-sm') {
  return `<span class="avatar ${size}" style="--avatar-bg:${esc(speaker.color)}">${esc(speaker.short || initials(speaker.name))}</span>`;
}

function applyReduceMotion() {
  document.documentElement.classList.toggle('reduce-motion', Boolean(db.settings?.reduceMotion));
}

/* ---------- 页面切换 ---------- */
function showPage(page) {
  if (promptOpen) closePromptSheet();
  if (!$('dialog').hidden) closeDialog();
  if (page !== 'scan') stopScanner();
  if (page !== 'meeting') stopSelfCamera(false);
  currentPage = page;
  document.querySelectorAll('.page').forEach(section => {
    section.hidden = section.dataset.page !== page;
  });
  const nav = $('bottom-nav');
  nav.hidden = !MAIN_PAGES.includes(page) || (page === 'meeting' && Boolean(db.active));
  document.querySelectorAll('[data-nav]').forEach(button => {
    const active = button.dataset.nav === page;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  const scroll = document.querySelector(`.page[data-page="${page}"] .page-scroll`);
  if (scroll) scroll.scrollTop = 0;

  if (page === 'home') renderHome();
  if (page === 'meeting') renderMeetingPage();
  if (page === 'history') renderHistory();
  if (page === 'profile') renderProfile();
  if (page === 'settings') renderSettings();
  if (page === 'scan') { resetScanPage(); startScanner(); }
}

/* ---------- 首页 ---------- */
function renderHome() {
  const greeting = new Date().getHours() < 12 ? '早上好' : new Date().getHours() < 18 ? '下午好' : '晚上好';
  if ($('home-title').firstChild) $('home-title').firstChild.nodeValue = `${greeting}，`;
  $('home-name').textContent = db.user.nickname;
  $('device-status').textContent = db.device.connected ? '设备已连接' : '设备未连接';
  $('device-dot').className = `status-dot ${db.device.connected ? 'ok' : ''}`;
  $('device-battery').textContent = `${db.device.battery}%`;
  $('home-quota').textContent = String(remainingMinutes(db));
  if (!reconnecting) $('reconnect-label').textContent = '重新连接机器人';

  const recent = [...db.meetings]
    .sort((a, b) => new Date(b.endedAt) - new Date(a.endedAt))
    .slice(0, 3);
  $('recent-list').innerHTML = recent.length
    ? recent.map(meetingRow).join('')
    : '<div class="empty-inline">还没有会议记录。加入或快速开始一场会议。</div>';

  renderUpcomingLists();
}

async function reconnectRobot() {
  if (reconnecting) return;
  reconnecting = true;
  const button = $('reconnect-robot');
  button.disabled = true;
  $('reconnect-label').textContent = '正在重新连接…';
  $('device-status').textContent = '正在重新连接…';
  $('device-dot').className = 'status-dot';
  await wait(1100);
  db.device.connected = true;
  persist(db);
  reconnecting = false;
  button.disabled = false;
  renderHome();
  toast('机器人已重新连接（演示）');
}

function meetingRow(meeting) {
  const date = new Date(meeting.endedAt);
  return `
    <div class="record-row">
      <button class="record-hit" type="button" data-meeting="${esc(meeting.id)}">
        <span class="record-date"><strong>${date.getDate()}</strong><span>${date.getMonth() + 1}月</span></span>
        <span class="record-main">
          <span class="record-title">${esc(meeting.title)}</span>
          <span class="record-meta">
            <span>${meeting.durationMin} 分钟</span>
            <span>${meeting.participants.length} 人</span>
            <span>${dayLabel(meeting.endedAt)}</span>
          </span>
          <span class="record-summary">${esc(meeting.summary)}</span>
        </span>
        <svg class="record-chev" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m9 6 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
      </button>
    </div>`;
}

function upcomingHTML() {
  return db.scheduled.map(schedule => `
    <article class="upcoming-row">
      <div class="upcoming-main">
        <span class="upcoming-time">${esc(scheduleLabel(schedule))}</span>
        <div class="upcoming-copy">
          <h3>${esc(schedule.title)}</h3>
          <p>${schedule.duration} 分钟 · 本地预约</p>
        </div>
      </div>
      <div class="upcoming-actions">
        <button type="button" data-cancel-schedule="${esc(schedule.id)}">取消</button>
        <button type="button" class="start" data-start-schedule="${esc(schedule.id)}">开始</button>
      </div>
    </article>`).join('');
}

function renderUpcomingLists() {
  const has = db.scheduled.length > 0;
  const html = upcomingHTML();
  for (const [section, count, list] of [
    ['upcoming-section', 'upcoming-count', 'upcoming-list'],
    ['meeting-upcoming-section', 'meeting-upcoming-count', 'meeting-upcoming-list']
  ]) {
    $(section).hidden = !has;
    $(count).textContent = has ? `${db.scheduled.length} 场` : '';
    $(list).innerHTML = html;
  }
}

/* ---------- 会议页 ---------- */
function renderMeetingPage() {
  const active = db.active;
  $('meeting-empty').hidden = Boolean(active);
  $('meeting-active').hidden = !active;
  renderUpcomingLists();
  if (!active) return;

  $('meeting-title').textContent = active.title;
  const source = {quick:'快速会议', join:'加入会议', scheduled:'预定会议', demo:'演示模式'}[active.source] || '示例会议';
  $('meeting-meta').textContent = `${active.participants.length} 人 · ${source}`;
  $('meeting-elapsed').textContent = elapsedLabel(active.startedAt);
  $('demo-banner').hidden = !active.isDemo;
  renderActiveMeeting();
}

function renderActiveMeeting() {
  const active = db.active;
  if (!active) return;
  renderStage(active);
  renderCapture(active);
  renderLiveTranscript(active);
  renderPending(active);
  $('meeting-elapsed').textContent = elapsedLabel(active.startedAt);
  if (promptOpen) renderPromptSheet();
}

function renderStage(meeting) {
  const latest = meeting.transcript[meeting.transcript.length - 1];
  const currentId = latest?.speakerId;
  const self = meeting.participants.find(person => person.id === 'p-lin') || meeting.participants[0];
  if (!stageId || !meeting.participants.some(person => person.id === stageId)) stageId = currentId || self.id;
  if (selfCameraOn) stageId = self.id;
  const person = speakerOf(meeting, stageId);
  const isSelf = person.id === self.id;
  const showPreview = selfCameraOn && isSelf;

  $('stage-main').style.setProperty('--stage-tint', person.tint);
  $('stage-avatar').style.setProperty('--stage-color', person.color);
  $('stage-avatar').textContent = person.short || initials(person.name);
  $('stage-avatar').hidden = showPreview;
  $('stage-preview').hidden = !showPreview;
  $('stage-name').textContent = person.name;
  $('stage-role').textContent = `${person.role}${person.id === currentId ? ' · 发言中' : ''}${showPreview ? ' · 本机预览' : ''}`;
  $('stage-tag').textContent = showPreview ? '摄像头' : person.id === currentId ? '发言中' : '参会者';
  $('preview-fallback').hidden = Boolean(selfCameraStream);
  $('stage-video').hidden = !selfCameraStream;

  $('filmstrip').innerHTML = meeting.participants.map(participant => {
    const classes = [
      participant.id === stageId ? 'focused' : '',
      participant.id === currentId ? 'speaking' : ''
    ].filter(Boolean).join(' ');
    return `<button type="button" class="${classes}" data-stage-id="${esc(participant.id)}" title="聚焦 ${esc(participant.name)}">
      ${avatar(participant, 'avatar-md')}
      <span class="participant-name">${esc(participant.name)}</span>
    </button>`;
  }).join('');
  $('attendee-count').textContent = String(meeting.participants.length);
  renderCameraButton();
  renderMicButton();
}

function renderCameraButton() {
  const button = $('live-camera');
  if (!button) return;
  button.setAttribute('aria-pressed', String(selfCameraOn));
  button.setAttribute('aria-label', selfCameraOn ? '关闭摄像头' : '开启摄像头');
  button.classList.toggle('on', selfCameraOn);
  $('live-camera-label').textContent = selfCameraOn ? '关闭视频' : '开启视频';
}

function renderMicButton() {
  const button = $('live-mic');
  if (!button) return;
  button.classList.toggle('muted', meetingMicMuted);
  button.setAttribute('aria-pressed', String(meetingMicMuted));
  button.setAttribute('aria-label', meetingMicMuted ? '解除静音' : '静音');
  $('live-mic-label').textContent = meetingMicMuted ? '解除静音' : '静音';
}

function toggleMic() {
  meetingMicMuted = !meetingMicMuted;
  renderMicButton();
  toast(meetingMicMuted ? '已静音（模拟）' : '已解除静音（模拟）');
}

async function toggleSelfCamera() {
  const active = db.active;
  if (!active) return;
  if (selfCameraOn) {
    stopSelfCamera();
    return;
  }
  selfCameraOn = true;
  stageId = 'p-lin';
  renderStage(active);
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('unsupported');
    selfCameraStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}});
    const video = $('stage-video');
    video.srcObject = selfCameraStream;
    await video.play().catch(() => {});
    renderStage(active);
    toast('摄像头已开启 · 仅本机预览');
  } catch {
    selfCameraStream = null;
    renderStage(active);
    toast('摄像头不可用，已显示模拟画面');
  }
}

function stopSelfCamera(render = true) {
  if (selfCameraStream) {
    selfCameraStream.getTracks().forEach(track => track.stop());
    selfCameraStream = null;
  }
  selfCameraOn = false;
  const video = $('stage-video');
  if (video) { video.srcObject = null; video.hidden = true; }
  if (render && currentPage === 'meeting' && db.active) renderStage(db.active);
  else renderCameraButton();
}

function renderCapture(meeting) {
  const capture = meeting.capture;
  $('shared-block').hidden = !capture;
  if (!capture) return;
  $('capture-image').src = capture.src;
  $('capture-image').alt = `现场共享内容：${capture.description}`;
  $('capture-desc').textContent = capture.description;
  $('capture-meta').textContent = `共享于 ${capture.at} · 原图由现场成员拍摄`;
}

function renderLiveTranscript(meeting) {
  const list = $('live-transcript');
  list.innerHTML = meeting.transcript.map((line, index) => {
    const person = speakerOf(meeting, line.speakerId);
    const latest = index === meeting.transcript.length - 1;
    return `
      <li class="transcript-item${latest ? ' latest' : ''}">
        <span class="transcript-time">${esc(line.at)}</span>
        <span class="transcript-copy">
          <span class="transcript-speaker" style="color:${esc(person.color)}">${esc(person.name)}</span>
          <p>${esc(line.text)}</p>
        </span>
      </li>`;
  }).join('');
  requestAnimationFrame(() => { list.scrollTop = list.scrollHeight; });
}

function renderPending(meeting) {
  const prompt = meeting.aiPrompt;
  const state = promptState(prompt);
  const pending = $('pending-list');
  if (!prompt) {
    $('pending-count').textContent = '0 条';
    pending.innerHTML = '<div class="pending-empty">暂无需要确认的 AI 提示。</div>';
    return;
  }
  $('pending-count').textContent = state === 'awaiting_confirmation' ? '1 条待确认' : '0 条待确认';
  const tone = state === 'expired' ? ' expired' : state === 'completed' ? ' done' : '';
  pending.innerHTML = `
    <article class="card pending-card">
      <h3>你的观点可能还没被现场听到</h3>
      <p>${esc(prompt.text)}</p>
      <div class="pending-bottom">
        <span class="pending-status${tone}">${esc(promptLabel(state))}</span>
        <button type="button" data-open-prompt>查看</button>
      </div>
    </article>`;
}

/* ---------- AI 候选弹层 ---------- */
function openPromptSheet() {
  const active = db.active;
  if (!active?.aiPrompt || promptOpen) return;
  if (!$('dialog').hidden) closeDialog();
  promptOpen = true;
  lastPromptState = promptState(active.aiPrompt);
  renderPromptSheet();
  $('overlay').hidden = false;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!promptOpen) return;
    $('overlay').classList.add('open');
    $('sheet').focus({preventScroll:true});
  }));
}

function closePromptSheet() {
  if (!promptOpen) return;
  promptOpen = false;
  $('overlay').classList.remove('open');
  clearTimeout(promptCloseTimer);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  promptCloseTimer = setTimeout(() => {
    if (promptOpen) return;
    $('overlay').hidden = true;
  }, reduced ? 0 : 280);
}

function renderPromptSheet() {
  if (!promptOpen) return;
  const prompt = db.active?.aiPrompt;
  if (!prompt) { closePromptSheet(); return; }
  const state = promptState(prompt);
  const seconds = remainingSeconds(prompt);
  $('sh-quote').textContent = prompt.text;
  $('sh-meta').textContent = `你说的 · 原话证据 ${prompt.evidenceIds?.length || 0} 条`;
  $('sh-state').textContent = promptLabel(state);
  $('sh-countdown').textContent = state === 'awaiting_confirmation'
    ? `${seconds} 秒内有效`
    : state === 'expired'
      ? '有效期已结束。点击「请机器人提醒」后会重新校验，仍满足条件才提交提醒。'
      : '本机模拟回执，不代表真实机器人已播报。';

  const actionable = state === 'awaiting_confirmation' || state === 'expired';
  const confirm = $('sh-confirm');
  const dismiss = $('sh-dismiss');
  confirm.disabled = promptBusy || !actionable;
  confirm.textContent = promptBusy ? (state === 'expired' ? '正在校验…' : '正在提交…') : '请机器人提醒';
  dismiss.hidden = state !== 'awaiting_confirmation';
  dismiss.disabled = promptBusy;
  $('sh-actions').classList.toggle('single', state !== 'awaiting_confirmation');
}

async function decidePrompt(decision) {
  const active = db.active;
  const prompt = active?.aiPrompt;
  if (!prompt || promptBusy) return;
  const state = promptState(prompt);

  if (decision === 'dismiss') {
    if (state !== 'awaiting_confirmation') return;
    prompt.state = 'dismissed';
    persist(db);
    closePromptSheet();
    renderPending(active);
    toast('已忽略本次 AI 提示');
    return;
  }

  if (state === 'expired') {
    promptBusy = true;
    renderPromptSheet();
    await wait(650);
    promptBusy = false;
    prompt.state = 'awaiting_confirmation';
    prompt.expiresAt = Date.now() + 120000;
    persist(db);
    renderActiveMeeting();
    toast('已重新校验，仍满足提醒条件');
    return;
  }

  if (state !== 'awaiting_confirmation') return;
  promptBusy = true;
  renderPromptSheet();
  await wait(700);
  promptBusy = false;
  prompt.state = 'queued';
  persist(db);
  renderActiveMeeting();

  clearPromptTimers();
  promptTimers.push(setTimeout(() => {
    if (db.active?.aiPrompt?.state !== 'queued') return;
    db.active.aiPrompt.state = 'broadcasting';
    persist(db);
    renderActiveMeeting();
  }, 2100));
  promptTimers.push(setTimeout(() => {
    if (db.active?.aiPrompt?.state !== 'broadcasting') return;
    db.active.aiPrompt.state = 'completed';
    persist(db);
    renderActiveMeeting();
  }, 4500));
}

/* ---------- 通用弹层 ---------- */
function openDialog({title, body, actions = [{label:'关闭', value:'close', style:'secondary'}], onAction}) {
  if (promptOpen) closePromptSheet();
  clearTimeout(dialogCloseTimer);
  $('dialog-title').textContent = title;
  $('dialog-body').innerHTML = body;
  $('dialog-actions').innerHTML = actions.map(action =>
    `<button type="button" class="button ${action.style || 'secondary'}" data-dialog-action="${esc(action.value)}">${esc(action.label)}</button>`
  ).join('');
  dialogHandler = onAction || null;
  $('dialog').hidden = false;
  requestAnimationFrame(() => $('dialog').classList.add('open'));
}

function closeDialog() {
  if ($('dialog').hidden) return;
  $('dialog').classList.remove('open');
  clearTimeout(dialogCloseTimer);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  dialogCloseTimer = setTimeout(() => {
    if ($('dialog').classList.contains('open')) return;
    $('dialog').hidden = true;
    dialogHandler = null;
  }, reduced ? 0 : 280);
}

/* ---------- 会议开始 / 结束 ---------- */
function guardActive(action) {
  if (!db.active) { action(); return; }
  openDialog({
    title:'已有进行中的会议',
    body:`<p>「${esc(db.active.title)}」还未结束。先结束并保存这场会议，再开始新的会议？</p>`,
    actions:[
      {label:'返回当前会议', value:'back', style:'secondary'},
      {label:'结束并开始', value:'end', style:'primary'}
    ],
    onAction: value => {
      if (value === 'back') { closeDialog(); showPage('meeting'); return; }
      if (value === 'end') {
        stopSelfCamera(false);
        const saved = endActiveMeeting(db);
        closeDialog();
        if (saved) toast('上一场会议已保存');
        action();
      }
    }
  });
}

function startTemplateMeeting({title, source, code = '', isDemo = false}) {
  closeDialog();
  closePromptSheet();
  clearPromptTimers();
  clearTimeout(autoPromptTimer);
  stopSelfCamera(false);
  stageId = null;
  selfCameraOn = false;
  meetingMicMuted = false;
  buildActiveMeeting(db, {title, source, code, isDemo});
  autoPromptOpened = false;
  lastPromptState = '';
  showPage('meeting');
  autoPromptTimer = setTimeout(() => {
    if (currentPage !== 'meeting' || !db.active || autoPromptOpened) return;
    autoPromptOpened = true;
    if (promptState(db.active.aiPrompt) === 'awaiting_confirmation') openPromptSheet();
  }, 1600);
}

function requestEndMeeting() {
  const active = db.active;
  if (!active) return;
  openDialog({
    title:'结束会议并保存记录？',
    body:`<p>结束后会保存<strong>会议纪要、观点图谱和完整转写</strong>，并可在历史中回看。</p>
          <p>${active.isDemo ? '这是演示会议，记录不会写入正式历史。' : '本次会议时长会计入本地演示额度。'}</p>`,
    actions:[
      {label:'继续会议', value:'close', style:'secondary'},
      {label:'结束会议', value:'end', style:'primary'}
    ],
    onAction: value => {
      if (value !== 'end') return;
      finishMeeting();
    }
  });
}

function finishMeeting() {
  const record = endActiveMeeting(db);
  stopSelfCamera(false);
  clearPromptTimers();
  clearTimeout(autoPromptTimer);
  closePromptSheet();
  closeDialog();
  if (!record) { toast('没有进行中的会议'); return; }
  detailMeeting = record;
  detailTab = 'minutes';
  detailReturn = record.isDemo ? 'profile' : 'history';
  renderDetail();
  showPage('detail');
  toast(record.isDemo ? '演示记录已保存，不会写入正式历史' : '会议已保存到历史');
}

function exitDemo() {
  openDialog({
    title:'退出演示模式？',
    body:'<p>本场演示内容不会保存到历史，也不会影响正式额度。</p>',
    actions:[
      {label:'继续演示', value:'close', style:'secondary'},
      {label:'退出演示', value:'exit', style:'primary'}
    ],
    onAction: value => {
      if (value !== 'exit') return;
      stopSelfCamera(false);
      db.active = null;
      persist(db);
      clearPromptTimers();
      clearTimeout(autoPromptTimer);
      closePromptSheet();
      closeDialog();
      showPage('home');
      toast('已退出演示，未保存记录');
    }
  });
}

/* ---------- 加入会议 ---------- */
function openJoin(returnPage = 'home', code = null) {
  joinReturn = returnPage;
  $('j-mid').value = code || 'recycle-review';
  $('j-name').value = db.user.nickname;
  $('j-err').hidden = true;
  $('j-submit-label').textContent = '进入会议';
  $('mic-permission-status').textContent = '允许使用麦克风，才能在会议中发言。';
  $('j-mic-label').textContent = '允许麦克风';
  $('cam-permission-status').textContent = '允许使用摄像头，才能在会议中开启画面。';
  $('j-cam-label').textContent = '允许摄像头';
  $('j-cam').disabled = false;
  joinCameraGranted = false;
  joinBusy = false;
  updateJoinAvailability();
  showPage('join');
}

async function authorizeJoinCamera() {
  const button = $('j-cam');
  button.disabled = true;
  $('j-cam-label').textContent = '检查中…';
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('unsupported');
    const stream = await navigator.mediaDevices.getUserMedia({video:true});
    stream.getTracks().forEach(track => track.stop());
    joinCameraGranted = true;
    $('cam-permission-status').textContent = '摄像头已授权；仅检查授权，不会上传画面。';
  } catch (error) {
    joinCameraGranted = false;
    $('cam-permission-status').textContent = error.name === 'NotAllowedError'
      ? '摄像头未获授权；会议中会显示模拟画面。'
      : '无法访问摄像头；会议中会显示模拟画面。';
  } finally {
    button.disabled = false;
    $('j-cam-label').textContent = '重新检查摄像头';
  }
}

function updateJoinAvailability() {
  let valid = false;
  try {
    valid = Boolean(parseMeetingId($('j-mid').value)) && Boolean($('j-name').value.trim());
  } catch {
    valid = false;
  }
  $('j-submit').disabled = joinBusy || !valid;
}

async function handleJoin(event) {
  event.preventDefault();
  if (joinBusy) return;
  const error = $('j-err');
  error.hidden = true;

  let meetingId;
  let nickname;
  try {
    meetingId = parseMeetingId($('j-mid').value);
    nickname = $('j-name').value.trim();
    if (!nickname) throw new Error('请填写你在会议中的名字。');
  } catch (caught) {
    error.textContent = caught.message;
    error.hidden = false;
    return;
  }

  joinBusy = true;
  updateJoinAvailability();
  $('j-submit-label').textContent = '正在连接…';
  try {
    await wait(700);
    db.user.nickname = nickname;
    persist(db);
    guardActive(() => startTemplateMeeting({title:'回收箱方案评审', source:'join', code:meetingId}));
  } finally {
    joinBusy = false;
    $('j-submit-label').textContent = '进入会议';
    updateJoinAvailability();
  }
}

/* ---------- 预定会议 ---------- */
function openSchedule(returnPage = 'home') {
  scheduleReturn = returnPage;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  $('s-title').value = '';
  $('s-date').min = localDateInput(new Date());
  $('s-date').value = localDateInput(tomorrow);
  $('s-time').value = '15:00';
  $('s-duration').value = '45';
  $('s-err').hidden = true;
  showPage('schedule');
}

function handleSchedule(event) {
  event.preventDefault();
  const error = $('s-err');
  error.hidden = true;
  const title = $('s-title').value.trim();
  const date = $('s-date').value;
  const time = $('s-time').value;
  const duration = Number($('s-duration').value);
  if (!title) {
    error.textContent = '请填写会议主题。';
    error.hidden = false;
    return;
  }
  if (!date || !time) {
    error.textContent = '请选择日期和时间。';
    error.hidden = false;
    return;
  }
  const when = new Date(`${date}T${time}:00`);
  if (Number.isNaN(when.getTime()) || when.getTime() < Date.now() - 60000) {
    error.textContent = '请选择未来的时间。';
    error.hidden = false;
    return;
  }
  addScheduled(db, {
    id:'s-' + Date.now(),
    title,
    date,
    time,
    duration,
    createdAt:new Date().toISOString()
  });
  renderUpcomingLists();
  showPage('home');
  toast('已保存本地预约（演示）');
}

/* ---------- 历史 ---------- */
function renderHistory() {
  $('history-search').value = historyQuery;
  document.querySelectorAll('#history-filters button').forEach(button => {
    button.classList.toggle('active', button.dataset.filter === historyFilter);
  });
  renderHistoryList();
}

function renderHistoryList() {
  const query = historyQuery.trim().toLowerCase();
  let list = [...db.meetings].sort((a, b) => new Date(b.endedAt) - new Date(a.endedAt));
  if (query) list = list.filter(meeting => meeting.title.toLowerCase().includes(query));
  if (historyFilter === 'week') {
    list = list.filter(meeting => Date.now() - new Date(meeting.endedAt).getTime() <= 7 * 86400000);
  }
  if (historyFilter === 'todos') {
    list = list.filter(meeting => meeting.todos.some(todo => !todo.done));
  }
  $('history-count').textContent = `${list.length} 场`;
  if (!list.length) {
    const hasFilter = Boolean(query) || historyFilter !== 'all';
    $('history-list').innerHTML = `
      <div class="history-empty">
        <p>${hasFilter ? '没有符合当前搜索或筛选条件的会议。' : '还没有保存的会议记录。'}</p>
        <button type="button" data-history-empty="${hasFilter ? 'clear' : 'home'}">${hasFilter ? '清除筛选' : '去开一场会议'}</button>
      </div>`;
    return;
  }
  $('history-list').innerHTML = list.map(meetingRow).join('');
}

/* ---------- 会议详情 ---------- */
function openDetail(meetingId, returnPage) {
  const meeting = findMeeting(db, meetingId);
  if (!meeting) { toast('找不到这场会议'); return; }
  detailMeeting = meeting;
  detailReturn = returnPage;
  detailTab = 'minutes';
  renderDetail();
  showPage('detail');
  $('detail-body').scrollTop = 0;
}

function renderDetail() {
  const meeting = detailMeeting;
  if (!meeting) return;
  $('detail-title').textContent = meeting.title;
  $('detail-meta').textContent = `${fullDate(meeting.startedAt)} · ${meeting.durationMin} 分钟 · ${meeting.participants.length} 人`;
  $('detail-demo').hidden = !meeting.isDemo;
  document.querySelectorAll('#detail-tabs button').forEach(button => {
    const active = button.dataset.tab === detailTab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  renderDetailBody();
}

function renderDetailBody() {
  const meeting = detailMeeting;
  if (!meeting) return;
  const body = $('detail-body');
  if (detailTab === 'minutes') body.innerHTML = renderMinutes(meeting);
  if (detailTab === 'graph') body.innerHTML = renderGraph(meeting);
  if (detailTab === 'transcript') body.innerHTML = renderTranscript(meeting);
  body.scrollTop = 0;
}

function renderMinutes(meeting) {
  const conclusions = meeting.conclusions.length
    ? `<ul class="conclusion-list">${meeting.conclusions.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`
    : '<p class="minutes-empty">暂无关键结论。</p>';
  const todos = meeting.todos.length
    ? `<ul class="todo-list">${meeting.todos.map(todo => `
        <li class="todo-item${todo.done ? ' done' : ''}">
          <input type="checkbox" id="todo-${esc(todo.id)}" data-todo-id="${esc(todo.id)}" ${todo.done ? 'checked' : ''}>
          <label for="todo-${esc(todo.id)}">${esc(todo.text)}<span class="todo-owner">${esc(todo.owner)}</span></label>
        </li>`).join('')}</ul>`
    : '<p class="minutes-empty">暂无待办事项。</p>';
  const aiPrompt = meeting.aiPrompt;
  const promptBlock = aiPrompt ? `
    <section class="detail-section">
      <h2>AI 提示</h2>
      <div class="summary-box" style="background:#FFF6F2;border-color:#F4D8CE">
        <p><strong>${esc(promptLabel(promptState(aiPrompt)))}</strong><br>${esc(aiPrompt.text)}</p>
      </div>
    </section>` : '';

  return `
    <section class="detail-section">
      <h2>会议摘要</h2>
      <div class="summary-box"><p>${esc(meeting.summary)}</p></div>
    </section>
    <section class="detail-section">
      <h2>关键结论</h2>
      ${conclusions}
    </section>
    <section class="detail-section">
      <h2>待办事项</h2>
      ${todos}
    </section>
    ${promptBlock}
    <p class="footnote">待办勾选会保存在本机；本页为演示记录，不代表真实会议结论。</p>`;
}

function renderGraph(meeting) {
  const topics = new Map();
  for (const viewpoint of meeting.viewpoints) {
    if (!topics.has(viewpoint.topic)) topics.set(viewpoint.topic, []);
    topics.get(viewpoint.topic).push(viewpoint);
  }
  if (!topics.size) return '<p class="minutes-empty">暂无观点记录。</p>';
  return [...topics.entries()].map(([topic, viewpoints]) => `
    <section class="affinity-topic">
      <header><h3>${esc(topic)}</h3><span>${viewpoints.length} 条观点</span></header>
      <div class="note-grid">
        ${viewpoints.map(viewpoint => {
          const person = speakerOf(meeting, viewpoint.speakerId);
          return `
            <button class="opinion-note" type="button" data-note-id="${esc(viewpoint.id)}"
              style="--note-bg:${esc(person.tint)};--note-color:${esc(person.color)}">
              <span class="note-speaker">${esc(person.name)}</span>
              <p>${esc(viewpoint.text)}</p>
              <span class="note-foot">
                <span class="note-status">${esc(viewpointStateLabel(viewpoint.status))}</span>
                <span class="note-hint">查看原话</span>
              </span>
            </button>`;
        }).join('')}
      </div>
    </section>`).join('') + '<p class="footnote">主题决定分组，颜色代表发言者。点击便签查看原话与证据。</p>';
}

function renderTranscript(meeting) {
  const evidenceIds = new Set();
  for (const viewpoint of meeting.viewpoints) {
    (viewpoint.evidenceIds || []).forEach(id => evidenceIds.add(id));
    (viewpoint.responseEvidenceIds || []).forEach(id => evidenceIds.add(id));
  }
  if (!meeting.transcript.length) return '<p class="minutes-empty">暂无转写记录。</p>';
  return `
    <section class="full-transcript">
      <header class="full-transcript-head">
        <h2>完整转写</h2>
        <span>按时间顺序 · ${meeting.transcript.length} 条</span>
      </header>
      <ol class="full-transcript-list">
        ${meeting.transcript.map(line => {
          const person = speakerOf(meeting, line.speakerId);
          return `
            <li class="full-line">
              <span class="full-time">${esc(line.at)}</span>
              <div class="full-body">
                <span class="full-speaker" style="color:${esc(person.color)}">${esc(person.name)} · ${esc(person.role)}</span>
                <p>${esc(line.text)}${evidenceIds.has(line.id) ? '<span class="evidence-link">证据</span>' : ''}</p>
              </div>
            </li>`;
        }).join('')}
      </ol>
    </section>
    <p class="footnote">完整转写按时间顺序排列，标记“证据”的句子被观点引用。</p>`;
}

function openNoteDialog(meeting, viewpoint) {
  const person = speakerOf(meeting, viewpoint.speakerId);
  const evidence = (viewpoint.evidenceIds || [])
    .map(id => meeting.transcript.find(line => line.id === id))
    .filter(Boolean);
  const responses = (viewpoint.responseEvidenceIds || [])
    .map(id => meeting.transcript.find(line => line.id === id))
    .filter(Boolean);

  const evidenceHTML = evidence.length
    ? `<div class="evidence-list">${evidence.map(line => {
        const speaker = speakerOf(meeting, line.speakerId);
        return `<article class="evidence-item">
          <header><span>${esc(speaker.name)}</span><span>${esc(line.at)}</span></header>
          <p>${esc(line.text)}</p>
        </article>`;
      }).join('')}</div>`
    : '<p class="evidence-empty">暂无关联原话</p>';

  const responseHTML = responses.length
    ? `<p class="dialog-subhead">现场回应</p><div class="evidence-list">${responses.map(line => {
        const speaker = speakerOf(meeting, line.speakerId);
        return `<article class="evidence-item">
          <header><span>${esc(speaker.name)}</span><span>${esc(line.at)}</span></header>
          <p>${esc(line.text)}</p>
        </article>`;
      }).join('')}</div>`
    : '';

  openDialog({
    title:'观点详情',
    body:`
      <div class="note-detail-meta">
        <span>${esc(person.name)} · ${esc(person.role)}</span>
        <span>${esc(viewpoint.topic)}</span>
        <span>${esc(viewpointStateLabel(viewpoint.status))}</span>
      </div>
      <p class="note-detail-text">${esc(viewpoint.text)}</p>
      <p class="dialog-subhead">原话证据</p>
      ${evidenceHTML}
      ${responseHTML}`,
    actions:[{label:'关闭', value:'close', style:'secondary'}]
  });
}

/* ---------- 扫码 ---------- */
function resetScanPage() {
  stopScanner();
  scanBusy = false;
  $('scan-video').hidden = true;
  $('scan-placeholder').hidden = false;
  $('scan-hint').textContent = '正在开启摄像头…';
}

function stopScanner() {
  clearTimeout(scanTimer);
  scanTimer = null;
  if (scanStream) {
    scanStream.getTracks().forEach(track => track.stop());
    scanStream = null;
  }
  const video = $('scan-video');
  if (video) { video.srcObject = null; video.hidden = true; }
}

async function startScanner() {
  if (scanBusy || scanStream) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    $('scan-hint').textContent = '当前浏览器无法使用摄像头扫描。';
    return;
  }
  scanBusy = true;
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}});
    if (currentPage !== 'scan') {
      scanStream.getTracks().forEach(track => track.stop());
      scanStream = null;
      return;
    }
    const video = $('scan-video');
    video.srcObject = scanStream;
    await video.play().catch(() => {});
    video.hidden = false;
    $('scan-placeholder').hidden = true;
    if ('BarcodeDetector' in window) {
      $('scan-hint').textContent = '将二维码放入框内，识别后自动进入会议。';
      detectScanCode();
    } else {
      $('scan-hint').textContent = '当前浏览器不支持自动识别二维码。';
    }
  } catch {
    scanStream = null;
    $('scan-hint').textContent = '无法使用摄像头，请检查浏览器权限后重新进入。';
  } finally {
    scanBusy = false;
  }
}

async function detectScanCode() {
  if (currentPage !== 'scan' || !scanStream || !('BarcodeDetector' in window)) return;
  try {
    const detector = new BarcodeDetector({formats:['qr_code']});
    const codes = await detector.detect($('scan-video'));
    if (codes.length) { handleScanValue(codes[0].rawValue); return; }
  } catch {
    // Keep the camera preview usable even if a frame cannot be decoded.
  }
  scanTimer = setTimeout(detectScanCode, 600);
}

function handleScanValue(raw) {
  let code;
  try {
    code = parseMeetingId(raw);
  } catch {
    $('scan-hint').textContent = '未识别到有效会议码，请重新对准二维码。';
    scanTimer = setTimeout(detectScanCode, 1200);
    return;
  }
  stopScanner();
  toast('已识别会议码 ' + code);
  openJoin('home', code);
}

function openAttendeesDialog() {
  const meeting = db.active;
  if (!meeting) return;
  const latest = meeting.transcript[meeting.transcript.length - 1];
  const currentId = latest?.speakerId;
  const rows = meeting.participants.map(person => {
    const isSelf = person.id === 'p-lin';
    const speaking = person.id === currentId;
    return `<div class="attendee-row">
      ${avatar(person, 'avatar-sm')}
      <div class="attendee-copy">
        <b>${esc(person.name)}${isSelf ? '（你）' : ''}</b>
        <small>${esc(person.role)}${speaking ? ' · 发言中' : ''}</small>
      </div>
      ${speaking ? '<span class="attendee-badge">发言中</span>' : ''}
    </div>`;
  }).join('');
  openDialog({
    title:`参会者（${meeting.participants.length}）`,
    body:`<div class="attendee-list">${rows}</div>`,
    actions:[{label:'关闭', value:'close', style:'secondary'}]
  });
}

function openMeetingMoreDialog() {
  openDialog({
    title:'更多',
    body:'<p>当前为本地模拟会议；可从这里查看观点地图或结束会议。</p>',
    actions:[
      {label:'观点地图', value:'map', style:'secondary'},
      {label:'结束会议', value:'end', style:'primary'}
    ],
    onAction: value => {
      if (value === 'map') {
        closeDialog();
        renderMap();
        showPage('map');
      }
      if (value === 'end') {
        closeDialog();
        requestEndMeeting();
      }
    }
  });
}

function openShare() {
  const active = db.active;
  if (!active) return;
  if (active.capture) {
    openLightbox();
    toast('共享内容 · 模拟画面');
  } else {
    toast('当前没有可共享的内容');
  }
}

/* ---------- 我的 ---------- */
function renderProfile() {
  const plan = PLANS[db.user.plan] || PLANS.free;
  $('profile-name').textContent = db.user.nickname;
  $('profile-avatar').textContent = initials(db.user.nickname);
  $('plan-badge').textContent = plan.label;
  const remaining = remainingMinutes(db);
  $('quota-remaining').textContent = String(remaining);
  $('quota-total').textContent = String(db.user.quotaTotal);
  $('quota-used').textContent = String(db.user.quotaUsed);
  $('quota-reset').textContent = resetLabel(db.user.quotaReset);
  const usedPercent = db.user.quotaTotal ? Math.min(100, Math.round(db.user.quotaUsed / db.user.quotaTotal * 100)) : 0;
  $('quota-bar').style.width = `${usedPercent}%`;
  $('quota-bar').parentElement.setAttribute('aria-valuemax', String(db.user.quotaTotal));
  $('quota-bar').parentElement.setAttribute('aria-valuenow', String(db.user.quotaUsed));
  document.querySelectorAll('[data-plan-current]').forEach(badge => {
    badge.classList.toggle('show', badge.dataset.planCurrent === db.user.plan);
  });
  $('upgrade-plan').textContent = db.user.plan === 'free' ? '模拟升级到高级版' : '切换回免费版（模拟）';
}

function renderSettings() {
  const settings = db.settings;
  for (const [key, id] of [['reminders', 'set-reminders'], ['sounds', 'set-sounds'], ['reduceMotion', 'set-motion']]) {
    const button = $(id);
    const on = Boolean(settings[key]);
    button.classList.toggle('on', on);
    button.setAttribute('aria-checked', String(on));
  }
  applyReduceMotion();
}

async function clearShellCache() {
  if (!('caches' in window)) { toast('当前环境没有离线缓存'); return; }
  try {
    const keys = await caches.keys();
    await Promise.all(keys.map(key => caches.delete(key)));
    toast('离线缓存已清除，会议记录未受影响');
  } catch {
    toast('缓存清除失败，请稍后重试');
  }
}

/* ---------- 导出 ---------- */
function exportMeeting(meeting) {
  if (!meeting) { toast('没有可导出的会议'); return; }
  const payload = {
    format:'effmeet2-evidence-export-v1',
    exported_at:new Date().toISOString(),
    meeting_id:meeting.id,
    title:meeting.title,
    mode:'local-demo',
    meeting,
    notice:'本地演示数据；保留原话与证据引用，AI 推测不是本人核对结果。'
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `EffMeet2-${meeting.id}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('已导出含原话证据的 JSON');
}

/* ---------- 图片 ---------- */
function openLightbox() {
  const capture = db.active?.capture;
  if (!capture) { toast('当前没有共享原图'); return; }
  $('lightbox-image').src = capture.src;
  $('lightbox-image').alt = capture.description;
  $('lightbox').hidden = false;
  $('lightbox-close').focus({preventScroll:true});
}

function closeLightbox() {
  $('lightbox').hidden = true;
}

/* ---------- 事件绑定 ---------- */
$('bottom-nav').addEventListener('click', event => {
  const button = event.target.closest('[data-nav]');
  if (button) showPage(button.dataset.nav);
});

$('act-join').addEventListener('click', () => openJoin('home'));
$('act-quick').addEventListener('click', () => guardActive(() => {
  startTemplateMeeting({title:'回收箱方案评审', source:'quick'});
  toast('已进入快速会议（模拟）');
}));
$('act-schedule').addEventListener('click', () => openSchedule('home'));
$('home-history').addEventListener('click', () => showPage('history'));
$('home-scan').addEventListener('click', () => showPage('scan'));
$('reconnect-robot').addEventListener('click', reconnectRobot);

$('empty-join').addEventListener('click', () => openJoin('meeting'));
$('empty-quick').addEventListener('click', () => guardActive(() => {
  startTemplateMeeting({title:'回收箱方案评审', source:'quick'});
  toast('已进入快速会议（模拟）');
}));

$('join-back').addEventListener('click', () => showPage(joinReturn));
$('schedule-back').addEventListener('click', () => showPage(scheduleReturn));
$('map-back').addEventListener('click', () => showPage('meeting'));
$('detail-back').addEventListener('click', () => showPage(detailReturn));

$('join-form').addEventListener('submit', handleJoin);
for (const id of ['j-mid', 'j-name']) {
  $(id).addEventListener('input', () => {
    $('j-err').hidden = true;
    updateJoinAvailability();
  });
}
$('j-mic').addEventListener('click', async () => {
  const button = $('j-mic');
  if (button.disabled) return;
  button.disabled = true;
  $('j-mic-label').textContent = '检查中…';
  await wait(650);
  $('mic-permission-status').textContent = '麦克风已授权（本机模拟）；不录音、不上传。';
  $('j-mic-label').textContent = '重新检查麦克风';
  button.disabled = false;
});
$('j-cam').addEventListener('click', authorizeJoinCamera);

$('schedule-form').addEventListener('submit', handleSchedule);

$('filmstrip').addEventListener('click', event => {
  const button = event.target.closest('[data-stage-id]');
  if (!button || !db.active) return;
  stageId = button.dataset.stageId;
  renderStage(db.active);
});

$('pending-list').addEventListener('click', event => {
  if (event.target.closest('[data-open-prompt]')) openPromptSheet();
});

$('end-meeting').addEventListener('click', requestEndMeeting);
$('exit-demo').addEventListener('click', exitDemo);
$('open-map').addEventListener('click', () => {
  if (!db.active) { toast('没有进行中的会议'); return; }
  renderMap();
  showPage('map');
});
$('map-export').addEventListener('click', () => exportMeeting(db.active));
$('live-camera').addEventListener('click', toggleSelfCamera);
$('live-mic').addEventListener('click', toggleMic);
$('live-share').addEventListener('click', openShare);
$('live-attendees').addEventListener('click', openAttendeesDialog);
$('live-more').addEventListener('click', openMeetingMoreDialog);
$('view-capture').addEventListener('click', openLightbox);
$('capture-button').addEventListener('click', openLightbox);

$('scrim').addEventListener('click', closePromptSheet);
$('sheet-close').addEventListener('click', closePromptSheet);
$('sheet-handle').addEventListener('click', closePromptSheet);
$('sh-confirm').addEventListener('click', () => decidePrompt('confirm'));
$('sh-dismiss').addEventListener('click', () => decidePrompt('dismiss'));

$('dialog-scrim').addEventListener('click', closeDialog);
$('dialog-close').addEventListener('click', closeDialog);
$('dialog-actions').addEventListener('click', event => {
  const button = event.target.closest('[data-dialog-action]');
  if (!button) return;
  const value = button.dataset.dialogAction;
  if (value === 'close') { closeDialog(); return; }
  if (dialogHandler) dialogHandler(value);
});

$('history-search').addEventListener('input', event => {
  historyQuery = event.target.value;
  renderHistoryList();
});
$('history-filters').addEventListener('click', event => {
  const button = event.target.closest('[data-filter]');
  if (!button) return;
  historyFilter = button.dataset.filter;
  document.querySelectorAll('#history-filters button').forEach(item => {
    item.classList.toggle('active', item.dataset.filter === historyFilter);
  });
  renderHistoryList();
});

$('detail-tabs').addEventListener('click', event => {
  const button = event.target.closest('[data-tab]');
  if (!button) return;
  detailTab = button.dataset.tab;
  document.querySelectorAll('#detail-tabs button').forEach(item => {
    const active = item.dataset.tab === detailTab;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', String(active));
  });
  renderDetailBody();
});
$('detail-export').addEventListener('click', () => exportMeeting(detailMeeting));
$('detail-body').addEventListener('change', event => {
  const input = event.target.closest('input[data-todo-id]');
  if (!input || !detailMeeting) return;
  updateTodo(db, detailMeeting.id, input.dataset.todoId, input.checked);
  input.closest('.todo-item')?.classList.toggle('done', input.checked);
});
$('detail-body').addEventListener('click', event => {
  const note = event.target.closest('[data-note-id]');
  if (!note || !detailMeeting) return;
  const viewpoint = detailMeeting.viewpoints.find(item => item.id === note.dataset.noteId);
  if (viewpoint) openNoteDialog(detailMeeting, viewpoint);
});

/* 扫码 */
$('scan-back').addEventListener('click', () => showPage('home'));

/* 设置 */
$('open-settings').addEventListener('click', () => showPage('settings'));
$('settings-back').addEventListener('click', () => showPage('profile'));
document.querySelectorAll('[data-setting]').forEach(button => {
  button.addEventListener('click', () => {
    const key = button.dataset.setting;
    db.settings[key] = !db.settings[key];
    persist(db);
    renderSettings();
    if (key === 'reduceMotion') applyReduceMotion();
    const labels = {reminders:'会议提醒', sounds:'提示音', reduceMotion:'减少动画'};
    const suffix = key === 'reduceMotion' ? '' : '（演示）';
    toast(`${labels[key]}已${db.settings[key] ? '开启' : '关闭'}${suffix}`);
  });
});
$('settings-language').addEventListener('click', () => {
  openDialog({
    title:'语言',
    body:'<p>当前版本仅提供简体中文。演示版没有多语言资源。</p>',
    actions:[{label:'关闭', value:'close', style:'secondary'}]
  });
});
$('settings-privacy').addEventListener('click', () => {
  openDialog({
    title:'隐私与数据',
    body:`<p>会议、观点、转写、AI 提示、额度与设置保存在当前浏览器的 <strong>localStorage</strong>（effmeet2.local.v1）。</p>
          <p>摄像头画面仅在本机用于预览和扫码，不会上传；会议音视频、AI、机器人与联系人未接入。</p>
          <p>清除浏览器数据或重置演示数据会删除本机记录。</p>`,
    actions:[{label:'关闭', value:'close', style:'secondary'}]
  });
});
$('settings-cache').addEventListener('click', clearShellCache);
$('settings-about').addEventListener('click', () => {
  openDialog({
    title:'关于 EffMeet 2',
    body:`<p><strong>EffMeet 2 手机端 · v1.0.0</strong><br>本地演示版</p>
          <p>包含首页、会议、历史、我的四个主页面，以及扫码加入、会议纪要、观点图谱和完整转写。</p>
          <p>所有会议与额度数据均为本地示例，不代表真实服务。</p>`,
    actions:[{label:'关闭', value:'close', style:'secondary'}]
  });
});

$('edit-name').addEventListener('click', () => {
  openDialog({
    title:'修改昵称',
    body:`<input class="dialog-field" id="dialog-input" maxlength="16" value="${esc(db.user.nickname)}" aria-label="昵称">
          <p class="field-hint">昵称只保存在本机，会同步到当前会议成员。</p>`,
    actions:[
      {label:'取消', value:'close', style:'secondary'},
      {label:'保存', value:'save', style:'primary'}
    ],
    onAction: value => {
      if (value !== 'save') return;
      const next = $('dialog-input').value.trim();
      if (!next) { toast('昵称不能为空'); return; }
      db.user.nickname = next;
      if (db.active) {
        const self = db.active.participants.find(person => person.id === 'p-lin');
        if (self) { self.name = next; self.short = initials(next); }
      }
      persist(db);
      closeDialog();
      renderProfile();
      renderHome();
      if (db.active && currentPage === 'meeting') renderActiveMeeting();
      toast('昵称已更新');
    }
  });
});

$('upgrade-plan').addEventListener('click', () => {
  const isFree = db.user.plan === 'free';
  openDialog({
    title: isFree ? '模拟升级到高级版' : '切换回免费版',
    body: isFree
      ? `<p>高级版演示套餐包含：每月 <strong>600 分钟</strong>、单次 <strong>180 分钟</strong>、历史<strong>永久保存</strong>与高级分析。</p>
         <p>本次升级仅切换本机演示状态，<strong>不接支付、不产生费用</strong>，也不代表正式价格。</p>`
      : `<p>切换回免费版后，本机额度恢复为 <strong>120 分钟</strong>，历史记录不会被删除。</p>
         <p>该操作仅影响本地演示数据。</p>`,
    actions:[
      {label:'取消', value:'close', style:'secondary'},
      {label:isFree ? '确认升级' : '切换回免费版', value:'change', style:'primary'}
    ],
    onAction: value => {
      if (value !== 'change') return;
      setPlan(db, isFree ? 'pro' : 'free');
      closeDialog();
      renderProfile();
      renderHome();
      toast(isFree ? '已切换为高级版演示套餐' : '已切换回免费版');
    }
  });
});

$('open-contacts').addEventListener('click', () => toast('联系人功能即将开放，敬请期待'));
$('open-demo').addEventListener('click', () => guardActive(() => {
  startTemplateMeeting({title:'演示 · 回收箱方案评审', source:'demo', isDemo:true});
  toast('演示模式 · 记录不会写入正式历史');
}));
$('reset-demo').addEventListener('click', () => {
  openDialog({
    title:'重置演示数据？',
    body:'<p>将清除本机保存的会议、预约、额度与提示状态，并恢复初始示例。该操作无法撤销。</p>',
    actions:[
      {label:'取消', value:'close', style:'secondary'},
      {label:'重置', value:'reset', style:'primary'}
    ],
    onAction: value => {
      if (value !== 'reset') return;
      stopSelfCamera(false);
      stopScanner();
      clearPromptTimers();
      clearTimeout(autoPromptTimer);
      closePromptSheet();
      db = resetDB();
      detailMeeting = null;
      historyQuery = '';
      historyFilter = 'all';
      applyReduceMotion();
      closeDialog();
      showPage('home');
      toast('演示数据已重置');
    }
  });
});

$('lightbox-scrim').addEventListener('click', closeLightbox);
$('lightbox-close').addEventListener('click', closeLightbox);

/* 会议记录与预约的委托点击 */
document.addEventListener('click', event => {
  const meetingButton = event.target.closest('[data-meeting]');
  if (meetingButton) {
    openDetail(meetingButton.dataset.meeting, currentPage === 'home' ? 'home' : 'history');
    return;
  }

  const startButton = event.target.closest('[data-start-schedule]');
  if (startButton) {
    const schedule = db.scheduled.find(item => item.id === startButton.dataset.startSchedule);
    if (!schedule) return;
    guardActive(() => {
      removeScheduled(db, schedule.id);
      startTemplateMeeting({title:schedule.title, source:'scheduled'});
      toast('已开始预定会议（模拟）');
    });
    return;
  }

  const cancelButton = event.target.closest('[data-cancel-schedule]');
  if (cancelButton) {
    const schedule = db.scheduled.find(item => item.id === cancelButton.dataset.cancelSchedule);
    if (!schedule) return;
    openDialog({
      title:'取消预约？',
      body:`<p>将删除「${esc(schedule.title)}」的本地预约记录。</p>`,
      actions:[
        {label:'保留', value:'close', style:'secondary'},
        {label:'取消预约', value:'cancel', style:'primary'}
      ],
      onAction: value => {
        if (value !== 'cancel') return;
        removeScheduled(db, schedule.id);
        closeDialog();
        renderUpcomingLists();
        toast('预约已取消');
      }
    });
    return;
  }

  const emptyButton = event.target.closest('[data-history-empty]');
  if (emptyButton) {
    if (emptyButton.dataset.historyEmpty === 'clear') {
      historyQuery = '';
      historyFilter = 'all';
      renderHistory();
    } else {
      showPage('home');
    }
  }
});

/* 左右滑动保留原有的会议 / 观点地图切换 */
let swipe = null;
for (const page of ['meeting', 'map']) {
  const element = document.querySelector(`.page[data-page="${page}"]`);
  element.addEventListener('pointerdown', event => {
    if (currentPage !== page) return;
    if (event.target.closest('button,a,input,select,summary,details')) return;
    swipe = {x:event.clientX, y:event.clientY};
  });
  element.addEventListener('pointerup', event => {
    if (!swipe || currentPage !== page) { swipe = null; return; }
    const dx = event.clientX - swipe.x;
    const dy = event.clientY - swipe.y;
    swipe = null;
    if (Math.abs(dx) <= 75 || Math.abs(dx) <= Math.abs(dy) * 1.6) return;
    if (page === 'meeting' && dx < 0 && db.active) {
      renderMap();
      showPage('map');
    }
    if (page === 'map' && dx > 0) showPage('meeting');
  });
  element.addEventListener('pointercancel', () => { swipe = null; });
}

function renderMap() {
  const meeting = db.active;
  if (!meeting) return;
  const total = meeting.viewpoints.length;
  const responded = meeting.viewpoints.filter(viewpoint => viewpoint.status === 'responded').length;
  $('stat-all').textContent = String(total);
  $('stat-responded').textContent = String(responded);
  $('stat-review').textContent = String(total - responded);
  $('map-list').innerHTML = meeting.viewpoints.map(viewpoint => {
    const person = speakerOf(meeting, viewpoint.speakerId);
    const tone = viewpoint.status === 'responded' ? 'ok' : ['uncertain', 'possibly_unresponded'].includes(viewpoint.status) ? 'warn' : '';
    const evidence = (viewpoint.evidenceIds || [])
      .map(id => meeting.transcript.find(line => line.id === id)).filter(Boolean);
    const responses = (viewpoint.responseEvidenceIds || [])
      .map(id => meeting.transcript.find(line => line.id === id)).filter(Boolean);
    return `
      <article class="card opinion-card map-card">
        <div class="opinion-head"><strong>${esc(person.name)} · ${esc(person.role)}</strong></div>
        <span class="tag ${tone}">${esc(viewpointStateLabel(viewpoint.status))}</span>
        <p class="opinion-text">${esc(viewpoint.text)}</p>
        ${responses.length ? `<p class="reply ok">${responses.map(line => `${esc(speakerOf(meeting, line.speakerId).name)}：${esc(line.text)}`).join('<br>')}</p>` : ''}
        ${viewpoint.status === 'uncertain' ? '<p class="reply">这条关系不确定，请会后核对</p>' : ''}
        <details>
          <summary>查看原话</summary>
          ${evidence.length ? evidence.map(line => `<p>${esc(speakerOf(meeting, line.speakerId).name)} · ${esc(line.at)}：${esc(line.text)}</p>`).join('') : '<p>暂无关联原话</p>'}
          ${responses.map(line => `<p>现场回应 · ${esc(speakerOf(meeting, line.speakerId).name)}：${esc(line.text)}</p>`).join('')}
        </details>
      </article>`;
  }).join('');
}

/* ---------- 计时与键盘 ---------- */
setInterval(() => {
  if (currentPage === 'meeting' && db.active) {
    $('meeting-elapsed').textContent = elapsedLabel(db.active.startedAt);
  }
}, 1000);

setInterval(() => {
  const prompt = db.active?.aiPrompt;
  if (!prompt) return;
  const state = promptState(prompt);
  if (state !== lastPromptState) {
    lastPromptState = state;
    if (currentPage === 'meeting') renderPending(db.active);
    if (promptOpen) renderPromptSheet();
  } else if (promptOpen) {
    renderPromptSheet();
  }
}, 1000);

document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  if (!$('lightbox').hidden) { closeLightbox(); return; }
  if (!$('dialog').hidden) { closeDialog(); return; }
  if (promptOpen) closePromptSheet();
});

/* ---------- 初始化 ---------- */
applyReduceMotion();
showPage('home');
renderUpcomingLists();
updateJoinAvailability();

if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  const swUrl = new URL('./sw.js', import.meta.url);
  const scope = new URL('./', import.meta.url).pathname;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(swUrl, {scope}).catch(() => {});
  });
}
