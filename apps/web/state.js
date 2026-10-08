// Adapt the existing controller DTOs without inventing AI/device state.
export function parseMeetingId(raw) {
  let value = String(raw ?? '').trim();
  if (/^https?:\/\//i.test(value)) {
    const url = new URL(value);
    if (url.username || url.password) throw new Error('邀请链接不能包含账号密码。');
    const hash = new URLSearchParams(url.hash.replace(/^#/, ''));
    value = url.searchParams.get('meeting_id') || url.searchParams.get('meeting') || url.searchParams.get('mid') || hash.get('meeting_id') || '';
    if (!value) {
      value = decodeURIComponent(url.pathname.split('/').filter(Boolean).at(-1) || '');
      if (['app', 'meetings', 'meeting', 'join'].includes(value)) value = '';
    }
  }
  if (!/^[a-zA-Z0-9_-]{1,128}$/.test(value)) throw new Error('请填写有效的会议 ID，或包含会议 ID 的邀请链接。');
  return value;
}
export function remainingSeconds(row, serverNow) {
  if (!Number.isFinite(row?.expires_at) || !Number.isFinite(serverNow)) return null;
  return Math.max(0, Math.ceil(row.expires_at - serverNow));
}
export function receiptState(receipts = []) {
  const status = receipts.at(-1)?.status;
  if (status === 'started') return 'broadcasting';
  if (['completed', 'failed', 'rejected'].includes(status)) return status;
  return 'queued';
}
export function effectiveState(row, commands = [], serverNow) {
  if (row.state === 'awaiting_confirmation' && remainingSeconds(row, serverNow) === 0) return 'expired';
  if (row.state !== 'queued') return row.state;
  const command = commands.find(c => c.command.intervention_id === row.candidate.intervention_id);
  return receiptState(command?.receipts);
}
export function candidateKey(row) { return row.candidate.intervention_id; }
export function shouldAutoOpen(row, {actor, visible, live, seen, serverNow}) {
  return visible && live && row.candidate.owner_speaker_id === actor &&
    row.state === 'awaiting_confirmation' && remainingSeconds(row, serverNow) > 0 &&
    !seen.has(candidateKey(row));
}
export const candidateLabels = {
  awaiting_confirmation: '等待你的决定',
  queued: '好的，等现场说完这句话就提醒',
  broadcasting: '正在提醒现场……',
  completed: '已提醒，现场回应会关联到你的观点',
  expired: '已过期，未打扰现场',
  dismissed: '不必提醒',
  responded: '现场已回应，不再提醒',
  stale: '现场已有新发言，请等待重新核对',
  failed: '提醒未完成，请核对现场情况',
  rejected: '提醒未执行，请核对现场情况',
};
export const viewpointLabels = {
  responded: '已回应（AI 推测，待本人核对）',
  possibly_unresponded: '可能未回应',
  uncertain: '需人工核对',
  no_analysis: '尚未核对',
};

// Horizontal navigation must not depend on arbitrary gesture speed.
export function swipeTarget(view, dx, dy) {
  if (Math.abs(dx) <= 75 || Math.abs(dx) <= Math.abs(dy) * 1.6) return null;
  if (view === "live" && dx < 0) return "map";
  if (view === "map" && dx > 0) return "live";
  return null;
}

// Status inspection keeps the action visible; expired candidates need server validation.
export function candidateActions(row, commands = [], serverNow) {
  const state = effectiveState(row, commands, serverNow);
  const seconds = remainingSeconds(row, serverNow);
  return {
    state,
    confirmMode: state === 'awaiting_confirmation' && seconds > 0 ? 'decision' :
      state === 'expired' ? 'recheck' : null,
    canDismiss: state === 'awaiting_confirmation' && seconds > 0,
  };
}
