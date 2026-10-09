"""Boundary tests for the temporary synthetic-only phone gateway."""
import unittest
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from apps.web.qa.gateway import COOKIE, create_gateway

MID = str(uuid4())
OTHER = str(uuid4())
CANDIDATE = str(uuid4())
CODE = "test-only-access-code-at-least-24-chars"


def gateway_client():
    upstream = FastAPI()
    received = []

    @upstream.get("/api/demo/session")
    def session():
        return {"mode": "mock", "profiles": [
            {"actor": "operator", "token": "operator-secret"},
            {"actor": "remote_1", "token": "remote-secret"},
            {"actor": "remote_2", "token": "other-secret"}]}

    @upstream.get("/api/demo/meetings/{meeting_id}/state")
    def state(meeting_id: str, request: Request):
        received.append((meeting_id, request.headers.get("authorization")))
        return {"meeting_id": meeting_id}

    @upstream.post("/api/v1/meetings/{meeting_id}/interventions/{candidate_id}/decision")
    def decision(meeting_id: str, candidate_id: str, request: Request):
        received.append((meeting_id, request.headers.get("authorization")))
        return {"ok": True}

    app = create_gateway("http://upstream", MID, CODE,
                         transport=httpx.ASGITransport(app=upstream))
    return TestClient(app, base_url="https://phone.example", follow_redirects=False), received


class PhoneGatewayTests(unittest.TestCase):
    def test_login_and_single_identity_only(self):
        client, _ = gateway_client()
        with client:
            assert client.get("/app/").status_code == 303
            assert client.get("/qa/login").status_code == 200
            assert client.post("/qa/login", data={"code": "no"}).status_code == 200
            response = client.post("/qa/login", data={"code": CODE})
            assert response.status_code == 303
            assert "Secure" in response.headers["set-cookie"]
            assert "HttpOnly" in response.headers["set-cookie"]
            assert "SameSite=strict" in response.headers["set-cookie"]
            assert client.cookies.get(COOKIE)
            session = client.get("/api/demo/session").json()
            assert session["mode"] == "mock"
            assert [x["actor"] for x in session["profiles"]] == ["remote_1"]
            assert session["profiles"][0]["token"] == "remote-secret"
            assert "operator-secret" not in str(session)
            assert "other-secret" not in str(session)


    def test_api_allowlist_and_owner_token(self):
        client, received = gateway_client()
        with client:
            client.post("/qa/login", data={"code": CODE})
            path = f"/api/demo/meetings/{MID}/state"
            assert client.get(path).status_code == 401
            assert client.get(path, headers={"Authorization": "Bearer operator-secret"}).status_code == 401
            assert client.get(path, headers={"Authorization": "Bearer remote-secret"}).json() == {"meeting_id": MID}
            assert received == [(MID, "Bearer remote-secret")]
            assert client.get(f"/api/demo/meetings/{OTHER}/state", headers={"Authorization": "Bearer remote-secret"}).status_code == 404
            assert client.post("/api/v1/meetings", json={"title": "intrusion"}).status_code == 404
            assert client.get("/docs").status_code == 404
            assert client.get("/app/qa/gateway.py").status_code == 404
            action = f"/api/v1/meetings/{MID}/interventions/{CANDIDATE}/decision"
            assert client.post(action, json={"decision": "confirm"}, headers={"Authorization": "Bearer remote-secret"}).status_code == 200
            assert received[-1] == (MID, "Bearer remote-secret")
            assert client.post(action, json={}, headers={"Authorization": "Bearer operator-secret"}).status_code == 401
            assert client.post(action, json={}, headers={"Authorization": "Bearer remote-secret", "Origin": "https://evil.example"}).status_code == 403


    def test_login_rate_limit_and_scope(self):
        client, _ = gateway_client()
        with client:
            for _ in range(8):
                assert client.post("/qa/login", data={"code": "wrong"}).status_code == 200
            assert client.post("/qa/login", data={"code": CODE}).status_code == 429
            assert client.get("/api/demo/session").status_code == 303
