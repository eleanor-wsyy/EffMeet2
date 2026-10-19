import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from deploy.livekit.token_service import (
    MockIdentityProvider,
    ProductionIdentityProvider,
    create_token_service,
)

ENV = {
    "LIVEKIT_API_KEY": "test-key",
    "LIVEKIT_API_SECRET": "a" * 32,
    "LIVEKIT_URL": "wss://rtc.example.test",
}


class TokenServiceTests(unittest.TestCase):
    def client(self, provider):
        return TestClient(create_token_service(provider))

    def test_mock_provider_issues_only_synthetic_remote_identities(self):
        with patch.dict(os.environ, ENV, clear=True):
            with self.client(MockIdentityProvider()) as client:
                ok = client.post("/rtc-token", json={"meeting_id": "meeting-1",
                                                     "identity": "remote_1"})
                self.assertEqual(ok.status_code, 200)
                body = ok.json()
                self.assertTrue(body["token"])
                self.assertEqual(body["room"], "meeting-1")
                self.assertEqual(body["url"], "wss://rtc.example.test")
                self.assertNotIn("secret", str(body).lower())

                denied = client.post("/rtc-token", json={"meeting_id": "meeting-1",
                                                         "identity": "operator"})
                self.assertEqual(denied.status_code, 403)
                self.assertEqual(denied.json()["error_code"], "REMOTE_IDENTITY_REQUIRED")

    def test_malformed_request_is_rejected(self):
        with patch.dict(os.environ, ENV, clear=True):
            with self.client(MockIdentityProvider()) as client:
                response = client.post("/rtc-token", json={"meeting_id": "meeting-1"})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error_code"], "BAD_REQUEST")

    def test_production_provider_stays_unavailable_until_wired(self):
        with patch.dict(os.environ, ENV, clear=True):
            with self.client(ProductionIdentityProvider()) as client:
                response = client.post("/rtc-token", json={"meeting_id": "meeting-1",
                                                           "identity": "remote_1"})
                self.assertEqual(response.status_code, 501)
                self.assertEqual(response.json()["error_code"], "AUTH_NOT_IMPLEMENTED")

    def test_missing_livekit_config_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.client(MockIdentityProvider()) as client:
                response = client.post("/rtc-token", json={"meeting_id": "meeting-1",
                                                           "identity": "remote_1"})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["error_code"], "LIVEKIT_NOT_CONFIGURED")
                health = client.get("/healthz").json()
                self.assertFalse(health["livekit_configured"])
                self.assertEqual(health["provider"], "mock")

    def test_healthz_reports_configured_provider(self):
        with patch.dict(os.environ, ENV, clear=True):
            with self.client(ProductionIdentityProvider()) as client:
                health = client.get("/healthz").json()
                self.assertTrue(health["livekit_configured"])
                self.assertEqual(health["provider"], "production")

    def test_mock_provider_refuses_public_bind(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "deploy/livekit/token_service.py"),
             "--host", "0.0.0.0", "--provider", "mock"],
            cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIn("loopback", result.stderr.lower())
