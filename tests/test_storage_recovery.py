"""Injected storage failures: no claim to reproduce a particular Windows driver bug."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import asyncio
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from services.controller.app import create_app
from services.controller.bench import Bench
from services.controller.contracts import DemoError
from services.controller.fakes import FakeAnalyzer
from services.controller.store import Store


CONNECT = sqlite3.connect


def storage_error(message="attempt to write a readonly database", code=sqlite3.SQLITE_READONLY):
    exc = sqlite3.OperationalError(message)
    exc.sqlite_errorcode = code
    return exc


@contextmanager
def fault_connections(*, fail_delete=False, fail_retry=False, code=sqlite3.SQLITE_READONLY,
                      fail_wal=False, rollback_failure=False):
    calls = {"faults": 0, "delete": 0}

    class FaultConnection(sqlite3.Connection):
        def execute(self, sql, *args):
            upper = sql.upper()
            if upper == "PRAGMA JOURNAL_MODE=DELETE":
                calls["delete"] += 1
                if fail_delete:
                    raise storage_error("journal mode cannot change while another process uses it", sqlite3.SQLITE_BUSY)
            target = upper == ("PRAGMA JOURNAL_MODE=WAL" if fail_wal else "BEGIN IMMEDIATE")
            if target and (not calls["faults"] or fail_retry):
                calls["faults"] += 1
                raise storage_error(code=code)
            return super().execute(sql, *args)

        def rollback(self):
            if rollback_failure:
                raise sqlite3.OperationalError("injected rollback failure")
            return super().rollback()

    def connect(*args, **kwargs):
        return CONNECT(*args, factory=FaultConnection, **kwargs)

    with patch("services.controller.store.sqlite3.connect", side_effect=connect):
        yield calls


class StorageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"main.db"
        self.env = patch.dict("os.environ", {"EFFMEET_SQLITE_JOURNAL_MODE": "WAL"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.store = Store(self.path)
        self.mid = self.store.create_meeting({"title": "synthetic recovery test"})["meeting_id"]

    def mode(self, store=None):
        with (store or self.store).db() as conn:
            return conn.execute("PRAGMA journal_mode").fetchone()[0]

    def test_fallback_is_verified_persistent_and_file_scoped(self):
        other = Store(Path(self.tmp.name)/"other.db")
        with fault_connections() as calls, self.assertLogs("services.controller.store", level="WARNING"):
            with self.store.db(write=True) as conn:
                conn.execute("UPDATE meetings SET title='updated' WHERE id=?", (self.mid,))
        self.assertEqual(calls["faults"], 1)
        self.assertEqual(calls["delete"], 1)
        self.assertEqual(self.mode(), "delete")
        self.assertEqual(self.mode(other), "wal")
        same = Store(self.path)
        self.assertIs(same._database, self.store._database)
        self.assertEqual(self.mode(same), "delete")
        with same.db() as conn:
            self.assertEqual(conn.execute("SELECT title FROM meetings WHERE id=?", (self.mid,)).fetchone()[0], "updated")

    def test_journal_initialization_failure_can_also_fallback(self):
        with fault_connections(fail_wal=True), self.assertLogs("services.controller.store", level="WARNING"):
            same = Store(self.path)
        self.assertEqual(self.mode(same), "delete")

    def test_busy_does_not_trigger_readonly_fallback(self):
        with fault_connections(code=sqlite3.SQLITE_BUSY) as calls, self.assertRaises(sqlite3.OperationalError):
            with self.store.db(write=True):
                self.fail("business SQL must not run")
        self.assertEqual(calls["delete"], 0)
        self.assertFalse(self.store._database.rollback_journal)

    def test_failed_mode_switch_preserves_original_and_does_not_set_success_flag(self):
        with fault_connections(fail_delete=True), self.assertRaises(sqlite3.OperationalError) as raised:
            with self.store.db(write=True):
                self.fail("business SQL must not run")
        self.assertEqual(raised.exception.sqlite_errorcode, sqlite3.SQLITE_READONLY)
        self.assertEqual(raised.exception.__cause__.sqlite_errorcode, sqlite3.SQLITE_BUSY)
        self.assertFalse(self.store._database.rollback_journal)

    def test_still_readonly_after_switch_is_not_reported_as_repaired(self):
        with fault_connections(fail_retry=True), self.assertRaises(sqlite3.OperationalError):
            with self.store.db(write=True):
                self.fail("business SQL must not run")
        self.assertFalse(self.store._database.rollback_journal)

    def test_transaction_body_is_never_replayed(self):
        count = 0
        with self.assertRaises(sqlite3.OperationalError):
            with self.store.db(write=True):
                count += 1
                raise storage_error()
        self.assertEqual(count, 1)
        self.assertEqual(self.mode(), "wal")

    def test_rollback_error_does_not_mask_original(self):
        original = ValueError("original business failure")
        with fault_connections(rollback_failure=True), self.assertLogs("services.controller.store"), self.assertRaises(ValueError) as raised:
            # Read connection avoids the injected BEGIN failure in this test.
            with self.store.db(write=True):
                raise original
        self.assertIs(raised.exception, original)

    def test_explicit_delete_mode_and_invalid_configuration(self):
        with patch.dict("os.environ", {"EFFMEET_SQLITE_JOURNAL_MODE": "DELETE"}):
            other = Store(Path(self.tmp.name)/"delete.db")
        self.assertEqual(self.mode(other), "delete")
        with patch.dict("os.environ", {"EFFMEET_SQLITE_JOURNAL_MODE": "invalid"}), self.assertRaises(ValueError):
            Store(Path(self.tmp.name)/"invalid.db")

    def test_concurrent_confirmation_with_fallback_dispatches_once(self):
        uid = str(uuid4())
        self.store.add_utterance(self.mid, {"utterance_id": uid, "stream_id": "manual",
            "speaker_id": "remote_1", "channel": "remote", "start_ms": 0, "end_ms": 1000,
            "text": "先验证草图。", "final": True, "revision": 1})
        candidate = self.store.analyze(self.mid, {"evidence_ids": [uid]}, "possibly_unresponded")["intervention"]
        with fault_connections(), self.assertLogs("services.controller.store", level="WARNING"):
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.store.decide(self.mid, candidate["intervention_id"],
                    {"decision": "confirm", "expected_revision": 1}, "remote_1"), range(4)))
        self.assertEqual(len({x["command"]["command_id"] for x in results}), 1)
        self.assertEqual(len(self.store.robot.calls), 1)

    def test_api_only_maps_known_storage_failures_to_retryable_503(self):
        app = create_app(self.path)
        with TestClient(app, raise_server_exceptions=False) as client:
            token = client.get("/api/demo/session").json()["profiles"][0]["token"]
            for code in [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_READONLY]:
                with patch.object(app.state.store, "create_meeting", side_effect=storage_error(code=code)), self.assertLogs("services.controller.app"):
                    response = client.post("/api/v1/meetings", json={"title": "test"}, headers={"Authorization": "Bearer " + token})
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.json()["error"]["retryable"])
            with patch.object(app.state.store, "create_meeting", side_effect=storage_error("no such table", sqlite3.SQLITE_ERROR)):
                response = client.post("/api/v1/meetings", json={"title": "test"}, headers={"Authorization": "Bearer " + token})
            self.assertEqual(response.status_code, 500)


class BenchFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name)/"bench.db")
        self.mid = self.store.create_meeting({"title": "synthetic bench failure"})["meeting_id"]
        self.uid = str(uuid4())
        self.store.add_utterance(self.mid, {"utterance_id": self.uid, "stream_id": "manual",
            "speaker_id": "remote_1", "channel": "remote", "start_ms": 0, "end_ms": 1000,
            "text": "先验证草图。", "final": True, "revision": 1})
        class Model:
            mode = "real"  # protocol stub only, not a real model
            def analyze(model, evidence, status):
                raise storage_error("original analyzer failure")
        self.runtime = Bench(self.store, Model())
        self.jid = self.runtime.enqueue(self.mid, {"evidence_ids": [self.uid]})["job_id"]

    def test_unexpected_failure_logs_original_traceback(self):
        with self.assertLogs("services.controller.bench", level="ERROR") as logs:
            self.assertTrue(self.runtime.work_once())
        self.assertIn("original analyzer failure", "\n".join(logs.output))
        self.assertEqual(self.runtime.job(self.mid, self.jid)["error_code"], "ANALYSIS_FAILED")

    def test_domain_error_keeps_code(self):
        with patch.object(self.runtime.analyzer, "analyze", side_effect=DemoError(409, "CONTEXT_CHANGED", "test")):
            self.runtime.work_once()
        self.assertEqual(self.runtime.job(self.mid, self.jid)["error_code"], "CONTEXT_CHANGED")

    def test_failure_persistence_retries_without_replaying_analysis(self):
        real_db = self.store.db
        writes = [0]
        @contextmanager
        def unavailable(*args, **kwargs):
            if kwargs.get("write"):
                writes[0] += 1
                if writes[0] > 1:
                    raise storage_error("failure state could not be saved")
            with real_db(*args, **kwargs) as conn:
                yield conn
        with patch.object(self.runtime.analyzer, "analyze", wraps=self.runtime.analyzer.analyze) as analyze:
            with patch.object(self.store, "db", side_effect=unavailable), self.assertLogs("services.controller.bench", level="ERROR") as logs:
                self.assertTrue(self.runtime.work_once())
                with self.assertRaises(sqlite3.OperationalError):
                    self.runtime.work_once()
                self.assertEqual(self.runtime.job(self.mid, self.jid)["status"], "failed")
            self.assertIn("failure state could not be saved", "\n".join(logs.output))
            self.assertFalse(self.runtime.work_once())
            self.assertEqual(analyze.call_count, 1)
        self.assertFalse(self.runtime._failed_jobs)
        with self.store.db() as conn:
            self.assertEqual(conn.execute("SELECT status FROM bench_jobs WHERE id=?", (self.jid,)).fetchone()[0], "failed")

    def test_worker_survives_storage_outage(self):
        calls = [0]
        def work():
            calls[0] += 1
            if calls[0] == 1:
                raise storage_error()
            raise asyncio.CancelledError()
        async def check():
            with patch.object(self.runtime, "work_once", side_effect=work):
                with self.assertLogs("services.controller.bench", level="ERROR"):
                    with self.assertRaises(asyncio.CancelledError):
                        await self.runtime.worker()
        asyncio.run(check())
        self.assertEqual(calls[0], 2)


if __name__ == "__main__":
    unittest.main()
