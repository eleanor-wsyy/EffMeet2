"""SQLite-backed mock controller. Transactions never call a real model or device."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4, uuid5, NAMESPACE_URL

from .contracts import DemoError, validate
from .fakes import FakeAnalyzer, FakeRobot


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Store:
    def __init__(self, path, analyzer=None, robot=None, clock=time.time, candidate_ttl=120):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.analyzer = analyzer or FakeAnalyzer()
        self.robot = robot or FakeRobot()
        if self.analyzer.mode != "mock" or self.robot.mode != "mock":
            raise ValueError("This demo cannot dispatch to real model/device adapters.")
        self.clock = clock
        self.candidate_ttl = candidate_ttl
        with self.db() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    seq INTEGER NOT NULL, data TEXT NOT NULL, UNIQUE(meeting_id, seq)
                );
                CREATE TABLE IF NOT EXISTS utterances (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    event_id TEXT REFERENCES events(id), data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    cache_key TEXT NOT NULL, result TEXT NOT NULL,
                    intervention_id TEXT, UNIQUE(meeting_id, cache_key)
                );
                CREATE TABLE IF NOT EXISTS interventions (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    claim_id TEXT UNIQUE REFERENCES analyses(id), owner TEXT NOT NULL,
                    candidate TEXT NOT NULL, candidate_event_id TEXT REFERENCES events(id),
                    state TEXT NOT NULL, revision INTEGER NOT NULL,
                    context_seq INTEGER NOT NULL, expires_at REAL NOT NULL,
                    request TEXT, decision TEXT, result TEXT
                );
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    intervention_id TEXT UNIQUE REFERENCES interventions(id), data TEXT NOT NULL,
                    receipts TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS summaries (
                    meeting_id TEXT PRIMARY KEY REFERENCES meetings(id),
                    context_seq INTEGER NOT NULL, data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS captures (
                    id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    event_id TEXT REFERENCES events(id), filename TEXT NOT NULL,
                    content_type TEXT NOT NULL, data BLOB NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audio_sessions (
                    session_id TEXT PRIMARY KEY, meeting_id TEXT REFERENCES meetings(id),
                    device_id TEXT NOT NULL, stream_id TEXT NOT NULL,
                    stream_key INTEGER NOT NULL, direction TEXT NOT NULL,
                    purpose TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'ready',
                    created_at TEXT NOT NULL, ended_at TEXT
                );
                CREATE TABLE IF NOT EXISTS device_tokens (
                    device_id TEXT PRIMARY KEY, token TEXT NOT NULL,
                    paired_at TEXT NOT NULL, meeting_id TEXT REFERENCES meetings(id)
                );
            """)

    @contextmanager
    def db(self, write=False):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.commit()
        except Exception:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def require_meeting(self, conn, meeting_id):
        row = conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        if row is None:
            raise DemoError(404, "MEETING_NOT_FOUND", "会议不存在。")
        return row

    def emit(self, conn, meeting_id, kind, payload, trace_id, source,
             producer="controller", parent=None):
        seq = conn.execute(
            "SELECT COALESCE(MAX(seq),0)+1 FROM events WHERE meeting_id=?", (meeting_id,)
        ).fetchone()[0]
        now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="milliseconds")
        event = {
            "schema_version": "1.0", "event_id": str(uuid4()), "meeting_id": meeting_id,
            "seq": seq, "occurred_at": now.replace("+00:00", "Z"),
            "received_at": now.replace("+00:00", "Z"), "trace_id": trace_id,
            "parent_event_id": parent, "producer": producer, "source": source,
            "mode": "mock", "event_type": kind, "payload": payload,
        }
        validate("EventEnvelope", event)
        conn.execute("INSERT INTO events VALUES (?,?,?,?)", (event["event_id"], meeting_id, seq, packed(event)))
        return event

    def context_seq(self, conn, meeting_id):
        return conn.execute("""
            SELECT COALESCE(MAX(e.seq),0) FROM events e
            JOIN utterances u ON u.event_id=e.id WHERE u.meeting_id=?
        """, (meeting_id,)).fetchone()[0]

    def create_meeting(self, request):
        validate("Meeting", request)
        meeting_id = str(uuid4())
        with self.db(write=True) as conn:
            conn.execute("INSERT INTO meetings VALUES (?,?)", (meeting_id, request["title"]))
            event = self.emit(conn, meeting_id, "meeting.started", request, str(uuid4()), "demo_controller")
        return {"meeting_id": meeting_id, "mode": "mock", "event": event}

    def add_utterance(self, meeting_id, request):
        validate("UtteranceFinal", request)
        if request["end_ms"] < request["start_ms"]:
            raise DemoError(422, "INVALID_INTERVAL", "end_ms不能小于start_ms。")
        if not request["text"].strip():
            raise DemoError(422, "EMPTY_TEXT", "发言不能只有空白。")
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            old = conn.execute("SELECT * FROM utterances WHERE id=?", (request["utterance_id"],)).fetchone()
            if old:
                if old["meeting_id"] != meeting_id or old["data"] != packed(request):
                    raise DemoError(409, "UTTERANCE_CONFLICT", "同一utterance_id不能对应不同内容或会议。")
                event = json.loads(conn.execute("SELECT data FROM events WHERE id=?", (old["event_id"],)).fetchone()[0])
                return {"event": event, "replayed": True}
            event = self.emit(conn, meeting_id, "utterance.final", request, str(uuid4()), "demo_manual_text", "web")
            conn.execute("INSERT INTO utterances VALUES (?,?,?,?)", (request["utterance_id"], meeting_id, event["event_id"], packed(request)))
        return {"event": event, "replayed": False}

    def analyze(self, meeting_id, request, status):
        validate("AnalysisRequest", request)
        if status not in {"responded", "possibly_unresponded", "uncertain"}:
            raise DemoError(422, "INVALID_SCENARIO", "未知模拟场景。")
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            rows = []
            for evidence_id in request["evidence_ids"]:
                row = conn.execute("""SELECT u.data, e.seq, e.id FROM utterances u
                    JOIN events e ON e.id=u.event_id WHERE u.id=? AND u.meeting_id=?""", (evidence_id, meeting_id)).fetchone()
                if row is None:
                    raise DemoError(422, "EVIDENCE_NOT_FOUND", "证据必须是本会议已落盘的最终发言。")
                rows.append(row)
            rows.sort(key=lambda x: x["seq"])
            context = self.context_seq(conn, meeting_id)
            key = hashlib.sha256(packed({"evidence_ids": sorted(request["evidence_ids"]), "context": context}).encode()).hexdigest()
            old = conn.execute("SELECT result FROM analyses WHERE meeting_id=? AND cache_key=?", (meeting_id, key)).fetchone()
            if old:
                result = json.loads(old[0])
                if result["analysis"]["status"] != status:
                    raise DemoError(409, "SCENARIO_CONFLICT", "同一上下文已有模拟结果；换场景请新建会议。")
                candidate = result["intervention"]
                if candidate:
                    pending = conn.execute("SELECT * FROM interventions WHERE id=?", (candidate["intervention_id"],)).fetchone()
                    if not pending["result"] and self.clock() >= pending["expires_at"]:
                        # Renew this still-unconfirmed candidate with a new revision.
                        # Old clients cannot confirm the expired revision, and a
                        # decided candidate can never be renewed/re-executed.
                        candidate = {**candidate, "state_revision": pending["revision"] + 1}
                        trace = str(uuid4())
                        renewed = self.emit(conn, meeting_id, "intervention.created", candidate, trace,
                                            "fake_analyzer", parent=pending["candidate_event_id"])
                        result = {**result, "intervention": candidate, "trace_id": trace, "replayed": False}
                        conn.execute("UPDATE interventions SET candidate=?,candidate_event_id=?,revision=?,expires_at=? WHERE id=?",
                                     (packed(candidate), renewed["event_id"], candidate["state_revision"],
                                      self.clock() + self.candidate_ttl, candidate["intervention_id"]))
                        conn.execute("UPDATE analyses SET result=? WHERE meeting_id=? AND cache_key=?", (packed(result), meeting_id, key))
                        return result
                return {**result, "replayed": True}
            evidence = [json.loads(x["data"]) for x in rows]
            analysis = self.analyzer.analyze(evidence, status)
            validate("AnalysisResult", analysis)
            trace = str(uuid4())
            analysis_event = self.emit(conn, meeting_id, "analysis.completed", analysis, trace, "fake_analyzer", parent=rows[0]["id"])
            candidate = None
            if analysis["status"] == "possibly_unresponded":
                candidate = {
                    "intervention_id": str(uuid4()), "claim_id": analysis["claim_id"],
                    "owner_speaker_id": analysis["owner_speaker_id"], "status": "awaiting_confirmation",
                    "state_revision": 1, "proposed_text": analysis["proposed_text"],
                    "evidence_ids": analysis["evidence_ids"],
                }
                validate("InterventionCandidate", candidate)
            result = {"trace_id": trace, "analysis": analysis, "intervention": candidate, "replayed": False}
            conn.execute("INSERT INTO analyses VALUES (?,?,?,?,?)", (
                analysis["claim_id"], meeting_id, key, packed(result),
                candidate["intervention_id"] if candidate else None,
            ))
            if candidate:
                event = self.emit(conn, meeting_id, "intervention.created", candidate, trace, "fake_analyzer", parent=analysis_event["event_id"])
                conn.execute("""INSERT INTO interventions (
                    id,meeting_id,claim_id,owner,candidate,candidate_event_id,state,revision,context_seq,expires_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                    candidate["intervention_id"], meeting_id, candidate["claim_id"], candidate["owner_speaker_id"],
                    packed(candidate), event["event_id"], "awaiting_confirmation", 1, context,
                    self.clock() + self.candidate_ttl,
                ))
        return result

    def decide(self, meeting_id, intervention_id, request, actor):
        validate("DecisionRequest", request)
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            row = conn.execute("SELECT * FROM interventions WHERE id=? AND meeting_id=?", (intervention_id, meeting_id)).fetchone()
            if row is None:
                raise DemoError(404, "CANDIDATE_NOT_FOUND", "候选不存在。")
            if actor != row["owner"]:
                raise DemoError(403, "NOT_OWNER", "只有该观点的线上本人可以确认或拒绝。")
            if row["result"]:
                if row["request"] != packed(request):
                    raise DemoError(409, "DECISION_CONFLICT", "候选已有最终决定，不能改写。")
                return {**json.loads(row["result"]), "replayed": True}
            if request["expected_revision"] != row["revision"]:
                raise DemoError(409, "STALE_REVISION", "候选版本已变化，请刷新。")
            if self.clock() >= row["expires_at"]:
                raise DemoError(409, "CANDIDATE_EXPIRED", "候选已过期，请重新分析。")
            if request["decision"] == "confirm" and self.context_seq(conn, meeting_id) != row["context_seq"]:
                raise DemoError(409, "CONTEXT_CHANGED", "有新发言进入会议，请重新分析后再确认。")
            revision = row["revision"] + 1
            decision = {"intervention_id": intervention_id, "actor_speaker_id": actor,
                        "decision": request["decision"], "state_revision": revision}
            trace = str(uuid4())
            event = self.emit(conn, meeting_id, "intervention.decided", decision, trace, "mock_session", "web", row["candidate_event_id"])
            result = {"event": event, "command": None, "receipts": [], "replayed": False}
            state = "dismissed"
            if request["decision"] == "confirm":
                candidate = json.loads(row["candidate"])
                command = {"command_id": str(uuid4()), "intervention_id": intervention_id,
                           "target_device_id": self.robot.device_id, "action": "speak", "ttl_ms": 5000,
                           "args": {"text": candidate["proposed_text"], "voice_profile": "mock_voice"}}
                validate("RobotCommand", command)
                cmd_event = self.emit(conn, meeting_id, "robot.command", command, trace, "demo_controller", parent=event["event_id"])
                # Mock-only, synchronous and inside this short transaction. A real-device
                # implementation needs an outbox/worker and must not use this dispatch path.
                try:
                    receipts = self.robot.execute(command)
                except Exception:
                    receipts = [{"command_id": command["command_id"], "target_device_id": self.robot.device_id,
                                 "boot_id": self.robot.boot_id, "status": "failed", "error_code": "MOCK_ADAPTER_ERROR"}]
                if not receipts or receipts[-1]["status"] not in {"completed", "failed", "rejected"}:
                    raise DemoError(500, "INVALID_MOCK_RECEIPT", "模拟设备未给出终态回执。")
                for receipt in receipts:
                    validate("RobotReceipt", receipt)
                    if receipt["command_id"] != command["command_id"] or receipt["target_device_id"] != command["target_device_id"]:
                        raise DemoError(500, "INVALID_MOCK_RECEIPT", "模拟回执不匹配命令。")
                    self.emit(conn, meeting_id, "robot.receipt", receipt, trace, "fake_robot", "robot", cmd_event["event_id"])
                conn.execute("INSERT INTO commands VALUES (?,?,?,?,?)", (command["command_id"], meeting_id, intervention_id, packed(command), packed(receipts)))
                state = "completed" if receipts[-1]["status"] == "completed" else "failed"
                result.update(command=command, receipts=receipts)
            conn.execute("UPDATE interventions SET state=?,revision=?,request=?,decision=?,result=? WHERE id=?", (
                state, revision, packed(request), request["decision"], packed(result), intervention_id,
            ))
        return result

    def events(self, meeting_id, after_seq=0):
        with self.db() as conn:
            self.require_meeting(conn, meeting_id)
            return [json.loads(x[0]) for x in conn.execute(
                "SELECT data FROM events WHERE meeting_id=? AND seq>? ORDER BY seq LIMIT 200", (meeting_id, after_seq)
            )]

    def snapshot(self, meeting_id):
        with self.db() as conn:
            meeting = self.require_meeting(conn, meeting_id)
            utterances = [json.loads(x[0]) for x in conn.execute("""SELECT u.data FROM utterances u
                JOIN events e ON e.id=u.event_id WHERE u.meeting_id=? ORDER BY e.seq""", (meeting_id,))]
            candidates = []
            for row in conn.execute("SELECT * FROM interventions WHERE meeting_id=? ORDER BY rowid", (meeting_id,)):
                state = row["state"]
                if state == "awaiting_confirmation":
                    if self.clock() >= row["expires_at"]:
                        state = "expired"
                    elif self.context_seq(conn, meeting_id) != row["context_seq"]:
                        state = "stale"
                candidates.append({"candidate": json.loads(row["candidate"]), "state": state,
                                   "state_revision": row["revision"], "decision": row["decision"]})
            commands = [{"command": json.loads(x["data"]), "receipts": json.loads(x["receipts"])}
                        for x in conn.execute("SELECT * FROM commands WHERE meeting_id=? ORDER BY rowid", (meeting_id,))]
        return {"meeting_id": meeting_id, "title": meeting["title"], "mode": "mock",
                "utterances": utterances, "interventions": candidates, "commands": commands}

    def add_capture(self, meeting_id, filename, content_type, image_data):
        capture_id = str(uuid4())
        now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="milliseconds")
        payload = {
            "capture_id": capture_id,
            "image_asset_id": str(uuid4()),
            "mime_type": content_type,
            "description": filename,
        }
        validate("Capture", payload)
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            event = self.emit(conn, meeting_id, "capture.created", payload, str(uuid4()), "demo_capture")
            conn.execute(
                "INSERT INTO captures VALUES (?,?,?,?,?,?,?)",
                (capture_id, meeting_id, event["event_id"], filename, content_type, image_data, now.replace("+00:00", "Z")),
            )
        return {"capture_id": capture_id, "event": event}

    def list_captures(self, meeting_id):
        with self.db() as conn:
            self.require_meeting(conn, meeting_id)
            return [
                {"capture_id": r["id"], "filename": r["filename"], "content_type": r["content_type"], "created_at": r["created_at"]}
                for r in conn.execute("SELECT * FROM captures WHERE meeting_id=? ORDER BY rowid", (meeting_id,))
            ]

    def get_capture(self, meeting_id, capture_id):
        with self.db() as conn:
            row = conn.execute(
                "SELECT * FROM captures WHERE id=? AND meeting_id=?", (capture_id, meeting_id)
            ).fetchone()
            if row is None:
                raise DemoError(404, "CAPTURE_NOT_FOUND", "图片不存在。")
            return row

    def open_audio_session(self, meeting_id, config):
        validate("AudioStreamConfig", config)
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            conn.execute(
                "INSERT INTO audio_sessions VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                (config["session_id"], meeting_id, config["device_id"], config["stream_id"],
                 config["stream_key"], config["direction"], config["purpose"], "ready", now),
            )
            ready = {"type": "audio.ready", "session_id": config["session_id"],
                     "stream_key": config["stream_key"], "accepted": True, "error_code": None}
            validate("AudioStreamReady", ready)
            event = self.emit(conn, meeting_id, "audio.session_opened", ready, str(uuid4()), "audio_gateway")
        return {"ready": ready, "event": event}

    def end_audio_session(self, meeting_id, end_request):
        validate("AudioStreamEnd", end_request)
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            row = conn.execute(
                "SELECT * FROM audio_sessions WHERE session_id=? AND meeting_id=?",
                (end_request["session_id"], meeting_id),
            ).fetchone()
            if row is None:
                raise DemoError(404, "SESSION_NOT_FOUND", "音频会话不存在。")
            if row["state"] == "ended":
                raise DemoError(409, "SESSION_ALREADY_ENDED", "音频会话已结束。")
            now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            conn.execute("UPDATE audio_sessions SET state='ended', ended_at=? WHERE session_id=?",
                         (now, end_request["session_id"]))
            event = self.emit(conn, meeting_id, "audio.session_ended", end_request, str(uuid4()), "audio_gateway")
        return {"event": event}

    def pair_device(self, meeting_id, device_id):
        import secrets as _secrets
        token = _secrets.token_urlsafe(32)
        now = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            conn.execute(
                "INSERT OR REPLACE INTO device_tokens VALUES (?,?,?,?)",
                (device_id, token, now, meeting_id),
            )
        return {"device_id": device_id, "media_token": token, "paired_at": now}

    def verify_device_token(self, device_id, token):
        with self.db() as conn:
            row = conn.execute(
                "SELECT * FROM device_tokens WHERE device_id=? AND token=?", (device_id, token)
            ).fetchone()
            return row is not None

    def build_viewpoint_map(self, meeting_id):
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            context = self.context_seq(conn, meeting_id)
            utterances = [json.loads(x[0]) for x in conn.execute("""SELECT u.data FROM utterances u
                JOIN events e ON e.id=u.event_id WHERE u.meeting_id=? ORDER BY e.seq""", (meeting_id,))]
            analyses = {}
            for row in conn.execute("SELECT result FROM analyses WHERE meeting_id=?", (meeting_id,)):
                result = json.loads(row[0])
                a = result["analysis"]
                analyses[a["claim_id"]] = a
            viewpoints = []
            for u in utterances:
                if not u["speaker_id"]:
                    continue
                matched = None
                for a in analyses.values():
                    if u["utterance_id"] in a["evidence_ids"] and a["owner_speaker_id"] == u["speaker_id"]:
                        matched = a
                        break
                vp = {
                    "viewpoint_id": str(uuid5(NAMESPACE_URL, meeting_id + u["utterance_id"])),
                    "speaker_id": u["speaker_id"],
                    "text": u["text"],
                    "evidence_ids": [u["utterance_id"]],
                    "response_status": matched["status"] if matched else "no_analysis",
                    "response_evidence_ids": matched["response_utterance_ids"] if matched else [],
                }
                viewpoints.append(vp)
            vmap = {
                "map_id": str(uuid4()),
                "meeting_id": meeting_id,
                "context_seq": context,
                "viewpoints": viewpoints,
            }
            validate("ViewpointMap", vmap)
            self.emit(conn, meeting_id, "viewpoint_map.updated", vmap, str(uuid4()), "deterministic_mock_viewpoint_map")
        return vmap

    def build_summary(self, meeting_id):
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            context = self.context_seq(conn, meeting_id)
            old = conn.execute("SELECT * FROM summaries WHERE meeting_id=?", (meeting_id,)).fetchone()
            if old and old["context_seq"] == context:
                return json.loads(old["data"])
            utterances = [json.loads(x[0]) for x in conn.execute("""SELECT u.data FROM utterances u
                JOIN events e ON e.id=u.event_id WHERE u.meeting_id=? ORDER BY e.seq""", (meeting_id,))]
            # Verbatim views only: no fabricated agreed decisions or human verification.
            items = [{"item_id": str(uuid5(NAMESPACE_URL, meeting_id + x["utterance_id"])),
                      "kind": "view", "speaker_id": x["speaker_id"], "text": x["text"],
                      "evidence_ids": [x["utterance_id"]], "verification_status": "unresolved"}
                     for x in utterances]
            summary = {"summary_id": str(uuid4()), "items": items}
            validate("Summary", summary)
            self.emit(conn, meeting_id, "summary.updated", summary, str(uuid4()), "deterministic_mock_summary")
            conn.execute("INSERT OR REPLACE INTO summaries VALUES (?,?,?)", (meeting_id, context, packed(summary)))
        return summary

    def read_summary(self, meeting_id):
        with self.db() as conn:
            self.require_meeting(conn, meeting_id)
            row = conn.execute("SELECT data FROM summaries WHERE meeting_id=?", (meeting_id,)).fetchone()
            if row is None:
                raise DemoError(404, "SUMMARY_NOT_FOUND", "先生成会后记录。")
            return json.loads(row[0])
