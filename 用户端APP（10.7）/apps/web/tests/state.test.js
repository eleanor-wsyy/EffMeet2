import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseMeetingId,remainingSeconds,effectiveState,receiptState,shouldAutoOpen,candidateKey} from '../state.js';

const row = (overrides = {}) => ({candidate:{intervention_id:'candidate-1',owner_speaker_id:'remote_1'},state:'awaiting_confirmation',state_revision:1,expires_at:1120,...overrides});
const context = (overrides = {}) => ({actor:'remote_1',visible:true,live:true,seen:new Set(),serverNow:1000,...overrides});
for (const [raw,expected] of [
  ['  meeting_1  ','meeting_1'],['f5b4ca70-034b-44f5-a3c1-44a791787789','f5b4ca70-034b-44f5-a3c1-44a791787789'],
  ['http://127.0.0.1:8765/app/?meeting_id=meet-1','meet-1'],['https://meet.example/meetings/abc/','abc'],
  ['https://meet.example/app/?meeting=hello','hello'],['https://meet.example/?mid=world','world'],
  ['https://meet.example/app/#meeting_id=hash-id','hash-id'],['https://meet.example/meetings/meet%2D1','meet-1'],
]) test('invite parsing: '+raw, () => assert.equal(parseMeetingId(raw),expected));
for (const raw of ['', '会议', 'javascript:alert(1)', 'file:///meeting', 'https://meet.example/app/', 'a'.repeat(129), 'bad/id', 'https://user:password@meet.example/?mid=ok', 'https://meet.example/meetings/abc%2Fdef']) {
  test('reject invalid invite: '+raw.slice(0,40), () => assert.throws(() => parseMeetingId(raw)));
}
test('server deadline is not restarted on reopen', () => {
  const r=row(); assert.equal(remainingSeconds(r,1000),120); assert.equal(remainingSeconds(r,1100),20);
  assert.equal(remainingSeconds(r,1119.1),1); assert.equal(remainingSeconds(r,1120),0);
  assert.equal(remainingSeconds({...r},1125),0); assert.equal(r.expires_at,1120);
});
test('missing deadline / server clock never makes an actionable reminder', () => {
  assert.equal(remainingSeconds(row({expires_at:undefined}),1000),null);
  assert.equal(remainingSeconds(row(),NaN),null);
  assert.equal(shouldAutoOpen(row({expires_at:undefined}),context()),false);
});
test('deadline locally expires even before next poll', () => assert.equal(effectiveState(row(),[],1120),'expired'));
test('only an eligible, visible, owned candidate can auto-open', () => {
  assert.equal(shouldAutoOpen(row(),context()),true);
  for (const override of [{actor:'remote_2'},{visible:false},{live:false},{serverNow:1120},{seen:new Set(['candidate-1'])}]) assert.equal(shouldAutoOpen(row(),context(override)),false);
  for (const state of ['queued','completed','stale','dismissed','expired','failed']) assert.equal(shouldAutoOpen(row({state}),context()),false);
});
test('seen identity survives same-ID renewed revision', () => {
  const r=row(); const seen=new Set([candidateKey(r)]);
  assert.equal(shouldAutoOpen(row({state_revision:2,expires_at:1240}),context({seen,serverNow:1130})),false);
});
test('real receipt drives queued, broadcasting, completed or failed', () => {
  for (const [receipts,expected] of [[[],'queued'],[[{status:'accepted'}],'queued'],[[{status:'started'}],'broadcasting'],[[{status:'started'},{status:'completed'}],'completed'],[[{status:'failed'}],'failed'],[[{status:'rejected'}],'rejected']]) {
    assert.equal(receiptState(receipts),expected);
    assert.equal(effectiveState(row({state:'queued'}),[{command:{intervention_id:'candidate-1'},receipts}],1000),expected);
  }
  assert.equal(effectiveState(row({state:'dismissed'}),[],1000),'dismissed');
});
test('a different candidate receipt does not affect this row', () => assert.equal(effectiveState(row({state:'queued'}),[{command:{intervention_id:'other'},receipts:[{status:'completed'}]}],1000),'queued'));
test('only three application screens; separate accessible sheet',async () => {
  const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
  assert.deepEqual([...html.matchAll(/id="view-([a-z]+)"/g)].map(m=>m[1]),['join','live','map']);
  assert.match(html,/role="dialog" aria-modal="true"/); assert.match(html,/id="j-mid"[^>]*required/);
  assert.match(html,/id="j-name"[^>]*required/); assert.match(html,/id="j-submit" disabled/);
  assert.doesNotMatch(html,/src="https?:/); assert.doesNotMatch(html,/onclick=/);
});
test('sheet moves up from bottom, never falls from above',async () => {
  const css=await readFile(new URL('../styles.css',import.meta.url),'utf8');
  assert.match(css,/transform:translateY\(100%\)/); assert.match(css,/\.open \.sheet\{transform:translateY\(0\)/);
  assert.doesNotMatch(css,/translateY\(-100%\)/); assert.match(css,/prefers-reduced-motion:reduce/);
});


test("horizontal navigation accepts slow gestures and rejects vertical scroll", async () => {
  const {swipeTarget} = await import("../state.js");
  assert.equal(swipeTarget("live", -230, 0), "map");
  assert.equal(swipeTarget("map", 230, 0), "live");
  assert.equal(swipeTarget("live", -70, 0), null);
  assert.equal(swipeTarget("live", -100, 100), null);
  assert.equal(swipeTarget("join", -230, 0), null);
  assert.equal(swipeTarget("live", 230, 0), null);
});

test('status dialog keeps confirm available for active or expired candidates only', async () => {
  const {candidateActions} = await import('../state.js');
  assert.equal(candidateActions(row(), [], 1000).confirmMode, 'decision');
  assert.equal(candidateActions(row(), [], 1120).confirmMode, 'recheck');
  assert.equal(candidateActions(row({state:'expired'}), [], 1121).confirmMode, 'recheck');
  assert.equal(candidateActions(row(), [], 1120).canDismiss, false);
  assert.equal(candidateActions(row({expires_at:undefined}), [], 1000).confirmMode, null);
  for (const state of ['queued','broadcasting','completed','dismissed','stale','failed','rejected','responded']) {
    assert.equal(candidateActions(row({state}), [], 1000).confirmMode, null);
  }
});
test('status action uses owner recheck before decision rather than client-side deadline reset', async () => {
  const js=await readFile(new URL('../app.js',import.meta.url),'utf8');
  assert.match(js, /'查看状态'/);
  assert.ok(js.includes("$('sh-actions').hidden = false"));
  assert.ok(js.indexOf("+ '/recheck'") < js.indexOf("+ '/decision'"));
  assert.ok(js.includes('Object.assign(row, renewed)'));
  assert.ok(!js.includes('row.expires_at ='));
});
