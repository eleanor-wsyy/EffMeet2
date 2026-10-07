"""Owner-verified response relationships. New speech alone never proves a reply."""
import json
from uuid import uuid4

from .contracts import DemoError, validate


class ResponseTracking:
    def claim_sources(self, conn, meeting_id, analysis):
        sources = []
        for uid in analysis["evidence_ids"]:
            row = conn.execute("""SELECT u.data,e.seq FROM utterances u JOIN events e ON e.id=u.event_id
                WHERE u.id=? AND u.meeting_id=?""", (uid, meeting_id)).fetchone()
            if row:
                utterance = json.loads(row["data"])
                if utterance["channel"] == "remote" and utterance["speaker_id"] == analysis["owner_speaker_id"]:
                    sources.append({**utterance, "seq": row["seq"]})
        return sources

    def verified_sources(self, conn, meeting_id):
        verified = {}
        for row in conn.execute("""SELECT v.data,a.result FROM response_verifications v
                JOIN analyses a ON a.id=v.claim_id WHERE v.meeting_id=? ORDER BY v.rowid""", (meeting_id,)):
            payload = json.loads(row["data"])
            analysis = json.loads(row["result"])["analysis"]
            for source in self.claim_sources(conn, meeting_id, analysis):
                verified[source["utterance_id"]] = payload
        return verified

    def response_is_verified(self, conn, meeting_id, analysis):
        sources = self.claim_sources(conn, meeting_id, analysis)
        verified = self.verified_sources(conn, meeting_id)
        return bool(sources) and all(u["utterance_id"] in verified for u in sources)

    def response_tracking(self, meeting_id):
        with self.db() as conn:
            self.require_meeting(conn, meeting_id)
            onsite = []
            for row in conn.execute("""SELECT u.data,e.seq FROM utterances u JOIN events e ON e.id=u.event_id
                    WHERE u.meeting_id=? ORDER BY e.seq""", (meeting_id,)):
                u = json.loads(row["data"])
                if u["channel"] == "onsite":
                    onsite.append({**u, "seq": row["seq"]})
            claims = []
            verified = self.verified_sources(conn, meeting_id)
            for row in conn.execute("SELECT * FROM analyses WHERE meeting_id=? ORDER BY rowid DESC", (meeting_id,)):
                analysis = json.loads(row["result"])["analysis"]
                sources = self.claim_sources(conn, meeting_id, analysis)
                verified_ids = sorted({rid for u in sources if u["utterance_id"] in verified
                    for rid in verified[u["utterance_id"]]["response_utterance_ids"]})
                complete = bool(sources) and all(u["utterance_id"] in verified for u in sources)
                claims.append({"claim_id": analysis["claim_id"], "owner_speaker_id": analysis["owner_speaker_id"],
                    "source_utterances": sources, "model_status": analysis["status"],
                    "model_response_ids": analysis["response_utterance_ids"],
                    "verification_status": "human_verified" if complete else "unresolved",
                    "response_status": "responded" if complete else analysis["status"],
                    "verified_response_ids": verified_ids,
                    "onsite_to_review": [u for u in onsite if u["seq"] > max((s["seq"] for s in sources), default=0)]})
            return {"meeting_id": meeting_id, "claims": claims}

    def verify_response(self, meeting_id, claim_id, request, actor):
        if set(request) != {"response_utterance_ids"}:
            raise DemoError(422, "INVALID_REQUEST", "只提交response_utterance_ids；身份由服务端确定。")
        payload = {"claim_id": claim_id, "actor_speaker_id": actor,
            "response_utterance_ids": request["response_utterance_ids"], "verification_status": "human_verified"}
        validate("ResponseVerification", payload)
        payload["response_utterance_ids"] = sorted(payload["response_utterance_ids"])
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.db(write=True) as conn:
            self.require_meeting(conn, meeting_id)
            row = conn.execute("SELECT result FROM analyses WHERE id=? AND meeting_id=?", (claim_id, meeting_id)).fetchone()
            if not row:
                raise DemoError(404, "CLAIM_NOT_FOUND", "观点不存在。")
            analysis = json.loads(row[0])["analysis"]
            if actor != analysis["owner_speaker_id"]:
                raise DemoError(403, "NOT_OWNER", "只有观点本人可确认回应关系。")
            old = conn.execute("SELECT data,event_id FROM response_verifications WHERE claim_id=?", (claim_id,)).fetchone()
            if old:
                if old["data"] != canonical:
                    raise DemoError(409, "VERIFICATION_CONFLICT", "该观点已有回应核对记录，不能静默改写。")
                event = json.loads(conn.execute("SELECT data FROM events WHERE id=?", (old["event_id"],)).fetchone()[0])
                return {"event": event, "replayed": True, "cancel_commands": []}
            sources = self.claim_sources(conn, meeting_id, analysis)
            cutoff = max((u["seq"] for u in sources), default=0)
            for rid in payload["response_utterance_ids"]:
                response = conn.execute("""SELECT u.data,e.seq FROM utterances u JOIN events e ON e.id=u.event_id
                    WHERE u.id=? AND u.meeting_id=?""", (rid, meeting_id)).fetchone()
                if not response or json.loads(response["data"])["channel"] != "onsite" or response["seq"] <= cutoff:
                    raise DemoError(422, "INVALID_RESPONSE_EVIDENCE", "回应必须是本会议中晚于原观点的现场发言。")
            event = self.emit(conn, meeting_id, "response.verified", payload, str(uuid4()), "owner_response_review", "web", mode="manual")
            conn.execute("INSERT INTO response_verifications VALUES (?,?,?,?)", (claim_id, meeting_id, canonical, event["event_id"]))
            # Derived summary must be regenerated even if no new utterance arrived.
            conn.execute("DELETE FROM summaries WHERE meeting_id=?", (meeting_id,))
            cancel = []
            for pending in conn.execute("""SELECT i.*,a.result AS analysis_result FROM interventions i
                    JOIN analyses a ON a.id=i.claim_id WHERE i.meeting_id=? AND i.state IN ('awaiting_confirmation','queued','playing')""", (meeting_id,)).fetchall():
                other = json.loads(pending["analysis_result"])["analysis"]
                if self.response_is_verified(conn, meeting_id, other):
                    if pending["state"] == "awaiting_confirmation":
                        conn.execute("UPDATE interventions SET state='responded',revision=revision+1 WHERE id=?", (pending["id"],))
                    else:
                        command = conn.execute("SELECT id FROM commands WHERE intervention_id=?", (pending["id"],)).fetchone()
                        if command:
                            cancel.append(command[0])
            return {"event": event, "replayed": False, "cancel_commands": cancel}
