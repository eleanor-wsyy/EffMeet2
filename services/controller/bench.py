"""Opt-in local bench: persistent analysis jobs and deferred device commands."""
import asyncio
from datetime import datetime
import hashlib
import json
import logging
import sqlite3
import threading
import secrets
import time
from uuid import uuid4

from .contracts import DemoError, validate
from .store import packed


class DeferredRobot:
    mode = "manual"
    deferred = True
    device_id = "host_speaker_test"
    boot_id = "00000000-0000-4000-8000-000000000000"


logger = logging.getLogger(__name__)


class Bench:
    def __init__(self, store, analyzer, tts=None):
        self.store, self.analyzer, self.tts = store, analyzer, tts
        self.active = {}
        self.speaking = set()
        self.last_voice = {}
        # Retain terminal errors while persistence is unavailable. Recovery on
        # process restart already marks interrupted jobs failed; never re-run AI.
        self._failed_jobs = {}
        self._failure_lock = threading.Lock()
        with store.db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS bench_jobs (
                    id TEXT PRIMARY KEY, meeting_id TEXT, cache_key TEXT UNIQUE,
                    context INTEGER, evidence TEXT, status TEXT, result TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS bench_bindings (
                    id TEXT PRIMARY KEY, config TEXT, speaker TEXT, channel TEXT,
                    start_ms INTEGER, expires REAL, state TEXT
                );
                CREATE TABLE IF NOT EXISTS bench_dispatch (
                    id TEXT PRIMARY KEY, boot_id TEXT, state TEXT, expires REAL, sink_mode TEXT NOT NULL DEFAULT 'manual'
                );
            """)
            if "sink_mode" not in {r[1] for r in conn.execute("PRAGMA table_info(bench_dispatch)")}:
                conn.execute("ALTER TABLE bench_dispatch ADD COLUMN sink_mode TEXT NOT NULL DEFAULT 'manual'")

    def recover(self):
        # Single process/worker only. Never replay an interrupted model or device task.
        with self.store.db(write=True) as conn:
            conn.execute("UPDATE bench_jobs SET status='failed',error='PROCESS_RESTARTED' WHERE status IN ('queued','running')")
            conn.execute("UPDATE bench_bindings SET state='closed' WHERE state='active'")
            rows = conn.execute("SELECT c.id FROM commands c JOIN interventions i ON i.id=c.intervention_id WHERE i.state IN ('queued','playing')").fetchall()
        for row in rows:
            self.fail_command(row["id"], "PROCESS_RESTARTED")

    def enqueue(self, meeting_id, request):
        validate("AnalysisRequest", request)
        with self.store.db(write=True) as conn:
            self.store.require_meeting(conn, meeting_id)
            context = self.store.context_seq(conn, meeting_id)
            evidence = []
            for uid in request["evidence_ids"]:
                row = conn.execute("SELECT data FROM utterances WHERE id=? AND meeting_id=?", (uid, meeting_id)).fetchone()
                if not row:
                    raise DemoError(422, "EVIDENCE_NOT_FOUND", "证据不在当前会议。")
                evidence.append(json.loads(row[0]))
            owners = {u["speaker_id"] for u in evidence if u["channel"] == "remote"}
            if len(owners) != 1 or None in owners:
                raise DemoError(422, "OWNER_UNCLEAR", "线上观点归属不明确。")
            key = hashlib.sha256(packed([meeting_id, context, sorted(request["evidence_ids"])]).encode()).hexdigest()
            old = conn.execute("SELECT id,status,result FROM bench_jobs WHERE cache_key=?", (key,)).fetchone()
            if old:
                renew = old["status"] == "failed"
                if old["status"] == "completed" and old["result"]:
                    candidate = json.loads(old["result"])["intervention"]
                    if candidate:
                        pending = conn.execute("SELECT state,expires_at FROM interventions WHERE id=?", (candidate["intervention_id"],)).fetchone()
                        renew = pending["state"] == "awaiting_confirmation" and time.time() >= pending["expires_at"]
                if renew:
                    conn.execute("UPDATE bench_jobs SET status='queued',result=NULL,error=NULL WHERE id=?", (old["id"],))
                    return {"job_id": old["id"], "status": "queued", "replayed": False}
                return {"job_id": old["id"], "status": old["status"], "replayed": True}
            if conn.execute("SELECT count(*) FROM bench_jobs WHERE status IN ('queued','running')").fetchone()[0] >= 32:
                raise DemoError(429, "QUEUE_FULL", "分析队列已满。")
            jid = str(uuid4())
            conn.execute("INSERT INTO bench_jobs VALUES (?,?,?,?,?,'queued',NULL,NULL)",
                         (jid, meeting_id, key, context, packed(evidence)))
        return {"job_id": jid, "status": "queued", "replayed": False}

    def job(self, mid, jid):
        with self.store.db() as conn:
            row = conn.execute("SELECT * FROM bench_jobs WHERE id=? AND meeting_id=?", (jid, mid)).fetchone()
        if not row:
            raise DemoError(404, "JOB_NOT_FOUND", "任务不存在。")
        with self._failure_lock:
            pending_error = self._failed_jobs.get(jid)
        if pending_error:
            return {"job_id": jid, "status": "failed", "result": None, "error_code": pending_error}
        return {"job_id": jid, "status": row["status"],
                "result": json.loads(row["result"]) if row["result"] else None, "error_code": row["error"]}

    def _persist_failure(self, jid, code):
        try:
            with self.store.db(write=True) as conn:
                conn.execute("UPDATE bench_jobs SET status='failed',error=? WHERE id=?", (code, jid))
        except Exception:
            logger.exception("Could not persist terminal failure for bench job %s; will retry", jid)
            return False
        with self._failure_lock:
            self._failed_jobs.pop(jid, None)
        return True

    def work_once(self):
        with self._failure_lock:
            pending = list(self._failed_jobs.items())
        for jid, code in pending:
            self._persist_failure(jid, code)
        with self.store.db(write=True) as conn:
            row = conn.execute("SELECT * FROM bench_jobs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
            if not row:
                return False
            conn.execute("UPDATE bench_jobs SET status='running' WHERE id=?", (row["id"],))
        try:
            if self.analyzer is None or self.analyzer.mode != "real":
                raise DemoError(503, "QWEN_NOT_CONFIGURED", "需配置真实模型。")
            evidence = json.loads(row["evidence"])
            # Network I/O is deliberately outside every SQLite transaction.
            result = self.analyzer.analyze(evidence, "uncertain")
            validate("AnalysisResult", result)
            ids = {u["utterance_id"] for u in evidence}
            owners = {u["speaker_id"] for u in evidence if u["channel"] == "remote"}
            onsite = {u["utterance_id"] for u in evidence if u["channel"] == "onsite"}
            if (result["owner_speaker_id"] not in owners or set(result["evidence_ids"]) != ids
                    or not set(result["response_utterance_ids"]) <= onsite
                    or (result["status"] == "responded") != bool(result["response_utterance_ids"])
                    or len(result["proposed_text"]) > 80):
                raise DemoError(422, "INVALID_MODEL_EVIDENCE", "模型证据校验失败。")
            committed = self.store.analyze(row["meeting_id"], {"evidence_ids": list(ids)}, result["status"],
                prepared=result, expected_context=row["context"])
            with self.store.db(write=True) as conn:
                conn.execute("UPDATE bench_jobs SET status='completed',result=? WHERE id=?", (packed(committed), row["id"]))
        except Exception as exc:
            if isinstance(exc, DemoError):
                code = exc.code
            else:
                logger.exception("Unexpected failure in bench job %s", row["id"])
                code = "ANALYSIS_FAILED"
            with self._failure_lock:
                self._failed_jobs[row["id"]] = code
            self._persist_failure(row["id"], code)
        return True

    async def worker(self):
        while True:
            try:
                if not await asyncio.to_thread(self.work_once):
                    await asyncio.sleep(0.1)
            except sqlite3.Error:
                logger.exception("Bench worker storage unavailable; retrying without replaying running jobs")
                await asyncio.sleep(0.5)

    def authenticate(self, device_id, token, meeting_id=None):
        with self.store.db() as conn:
            row = conn.execute("SELECT * FROM device_tokens WHERE device_id=?", (device_id,)).fetchone()
        if (not row or not token or not secrets.compare_digest(row["token"], token)
                or (meeting_id is not None and row["meeting_id"] != meeting_id)
                or time.time() - datetime.fromisoformat(row["paired_at"].replace("Z", "+00:00")).timestamp() > 3600):
            raise DemoError(401, "INVALID_MEDIA_TOKEN", "配对凭据无效或已过期，请重新配对。")
        return row["meeting_id"]

    def bind(self, meeting_id, body):
        config = body.get("config")
        validate("AudioStreamConfig", config)
        speaker, channel, start = body.get("speaker_id"), body.get("channel"), body.get("start_ms", 0)
        validate("UtteranceFinal", {"utterance_id": str(uuid4()), "stream_id": config["stream_id"],
            "speaker_id": speaker, "channel": channel, "start_ms": start, "end_ms": start,
            "text": "binding", "final": True, "revision": 1})
        if config["meeting_id"] != meeting_id or config["purpose"] != "onsite_voice":
            raise DemoError(422, "INVALID_BINDING", "此入口只接设备采集上行流；来源由主持人绑定。")
        if channel == "remote" and speaker not in {"remote_1", "remote_2"}:
            raise DemoError(422, "UNKNOWN_REMOTE", "本机台架只支持已知线上测试身份。")
        with self.store.db(write=True) as conn:
            self.store.require_meeting(conn, meeting_id)
            pair = conn.execute("SELECT meeting_id FROM device_tokens WHERE device_id=?", (config["device_id"],)).fetchone()
            if not pair or pair[0] != meeting_id:
                raise DemoError(403, "DEVICE_NOT_PAIRED", "请先为当前会议配对设备。")
            if conn.execute("SELECT 1 FROM bench_bindings WHERE id=?", (config["session_id"],)).fetchone():
                raise DemoError(409, "SESSION_REUSED", "新连接必须使用新session_id。")
            conn.execute("INSERT INTO bench_bindings VALUES (?,?,?,?,?,?,'ready')",
                (config["session_id"], packed(config), speaker, channel, start, time.time() + 600))
        return {"session_id": config["session_id"], "expires_in_seconds": 600}

    def claim_binding(self, config, token):
        self.authenticate(config["device_id"], token, config["meeting_id"])
        with self.store.db(write=True) as conn:
            row = conn.execute("SELECT * FROM bench_bindings WHERE id=?", (config["session_id"],)).fetchone()
            if not row or row["state"] != "ready" or row["expires"] <= time.time() or row["config"] != packed(config):
                raise DemoError(409, "INVALID_SESSION", "音频会话未绑定、已使用或不匹配。")
            conn.execute("UPDATE bench_bindings SET state='active' WHERE id=?", (config["session_id"],))
            return dict(row)

    def close_binding(self, sid):
        with self.store.db(write=True) as conn:
            conn.execute("UPDATE bench_bindings SET state='closed' WHERE id=?", (sid,))

    def command(self, cid):
        with self.store.db() as conn:
            row = conn.execute("""SELECT c.*,i.state,i.context_seq,i.expires_at FROM commands c
                JOIN interventions i ON i.id=c.intervention_id WHERE c.id=?""", (cid,)).fetchone()
            if not row:
                raise DemoError(404, "COMMAND_NOT_FOUND", "命令不存在。")
            return dict(row)

    def claim_command(self, cid, device, token, boot, sink_mode="manual"):
        if sink_mode not in {"manual", "mock"}:
            raise DemoError(422, "INVALID_SINK_MODE", "台架播放器必须声明manual或mock。")
        row = self.command(cid)
        self.authenticate(device, token, row["meeting_id"])
        command = json.loads(row["data"])
        validate("RobotReceipt", {"command_id": cid, "target_device_id": device,
            "boot_id": boot, "status": "accepted", "error_code": None})
        with self.store.db(write=True) as conn:
            state = conn.execute("SELECT state FROM interventions WHERE id=?", (row["intervention_id"],)).fetchone()[0]
            if state != "queued" or command["target_device_id"] != device:
                raise DemoError(409, "COMMAND_NOT_QUEUED", "命令已执行、取消或目标不匹配。")
            claim = conn.execute("SELECT a.result FROM analyses a JOIN interventions i ON i.claim_id=a.id WHERE i.id=?", (row["intervention_id"],)).fetchone()
            if self.store.response_is_verified(conn, row["meeting_id"], json.loads(claim[0])["analysis"]):
                raise DemoError(409, "ALREADY_RESPONDED", "观点已核对回应，不再播放。")
            if time.time() >= row["expires_at"] or self.store.context_seq(conn, row["meeting_id"]) != row["context_seq"]:
                raise DemoError(409, "STALE_COMMAND", "上下文已变化或候选过期。")
            conn.execute("UPDATE interventions SET state='playing' WHERE id=?", (row["intervention_id"],))
            conn.execute("INSERT INTO bench_dispatch (id,boot_id,state,expires,sink_mode) VALUES (?,?,'active',?,?)", (cid, boot, time.time() + command["ttl_ms"] / 1000, sink_mode))
        return command, row["meeting_id"]

    def receipt(self, receipt, *, terminal_override=False):
        validate("RobotReceipt", receipt)
        cid = receipt["command_id"]
        with self.store.db(write=True) as conn:
            row = conn.execute("SELECT * FROM commands WHERE id=?", (cid,)).fetchone()
            if not row:
                raise DemoError(404, "COMMAND_NOT_FOUND", "命令不存在。")
            command = json.loads(row["data"])
            history = json.loads(row["receipts"])
            if history and history[-1]["status"] in {"completed", "failed", "rejected"}:
                if history[-1] == receipt:
                    return
                raise DemoError(409, "COMMAND_TERMINAL", "命令已终止。")
            dispatch = conn.execute("SELECT * FROM bench_dispatch WHERE id=?", (cid,)).fetchone()
            expected = "accepted" if not history else "started" if history[-1]["status"] == "accepted" else "completed"
            if receipt["target_device_id"] != command["target_device_id"] or (dispatch and receipt["boot_id"] != dispatch["boot_id"]):
                raise DemoError(409, "RECEIPT_MISMATCH", "设备回执不匹配。")
            if not terminal_override and receipt["status"] not in {expected, "failed", "rejected"}:
                raise DemoError(409, "RECEIPT_ORDER", "设备回执顺序非法。")
            if receipt["status"] in {"failed", "rejected"} and not receipt["error_code"]:
                raise DemoError(422, "ERROR_CODE_REQUIRED", "失败回执需要错误码。")
            if receipt["status"] in {"accepted", "started", "completed"} and receipt["error_code"] is not None:
                raise DemoError(422, "INVALID_RECEIPT", "成功回执不能带错误码。")
            history.append(receipt)
            conn.execute("UPDATE commands SET receipts=? WHERE id=?", (packed(history), cid))
            self.store.emit(conn, row["meeting_id"], "robot.receipt", receipt, str(uuid4()), "bench_player", "robot", mode=dispatch["sink_mode"] if dispatch else "manual")
            if receipt["status"] in {"completed", "failed", "rejected"}:
                conn.execute("UPDATE interventions SET state=? WHERE id=?", (receipt["status"], row["intervention_id"]))
                conn.execute("UPDATE bench_dispatch SET state='closed' WHERE id=?", (cid,))

    def fail_command(self, cid, code):
        row = self.command(cid)
        if row["state"] not in {"queued", "playing"}:
            return
        with self.store.db() as conn:
            dispatch = conn.execute("SELECT boot_id FROM bench_dispatch WHERE id=?", (cid,)).fetchone()
        self.receipt({"command_id": cid, "target_device_id": json.loads(row["data"])["target_device_id"],
            "boot_id": dispatch[0] if dispatch else DeferredRobot.boot_id,
            "status": "failed", "error_code": code}, terminal_override=True)
