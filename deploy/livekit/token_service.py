"""Public LiveKit token service (deployment skeleton). NOT-VERIFIED.

Productionizes services/relay/livekit_token.issue_token behind an authentication
seam. The current bench gates identity to the synthetic {remote_1, remote_2}
test profiles (services/controller/app.py: livekit_token); a public gateway must
replace that with real account auth before exposing token issuance.

This file is a SKELETON:
  - MockIdentityProvider reproduces the current synthetic-only behaviour.
  - ProductionIdentityProvider is a NOT-VERIFIED stub that raises until wired to
    the real account system. Do not deploy it as-is.
  - The server binds loopback by default; public exposure requires TLS + auth.

Run (loopback, mock identity, requires LIVEKIT_* env):
    python deploy/livekit/token_service.py --port 8790
"""
import argparse
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Reuse the existing, tested token signer; never duplicate JWT logic here.
from services.relay.livekit_token import issue_token
from services.controller.contracts import DemoError

SYNTHETIC_REMOTE_IDS = {"remote_1", "remote_2"}


class IdentityError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


class MockIdentityProvider:
    """Reproduces the bench behaviour: only synthetic remote test identities.
    NOT production authentication."""

    name = "mock"

    def authorize(self, request: Request, meeting_id: str, identity: str):
        if identity not in SYNTHETIC_REMOTE_IDS:
            raise IdentityError(403, "REMOTE_IDENTITY_REQUIRED",
                                "mock provider only issues for synthetic remote test identities")
        # The bench also requires a valid test-session actor token; a public
        # gateway must enforce the real account check instead. See app.py:actor().
        return {"identity": identity, "meeting_id": meeting_id, "actor": identity}


class ProductionIdentityProvider:
    """NOT-VERIFIED stub. Wire to the real account/session system before use.

    Responsibilities at bring-up:
      - authenticate the caller (session cookie / OIDC / signed JWT),
      - confirm the caller is a participant of `meeting_id`,
      - return the canonical identity to bind into the LiveKit token,
      - reject cross-meeting and impersonation attempts.
    """

    name = "production"

    def authorize(self, request: Request, meeting_id: str, identity: str):
        raise IdentityError(501, "AUTH_NOT_IMPLEMENTED",
                            "ProductionIdentityProvider is a NOT-VERIFIED stub; "
                            "wire real account auth before public deployment")


def create_token_service(provider=None):
    provider = provider or MockIdentityProvider()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz():
        configured = bool(os.environ.get("LIVEKIT_URL")
                          and os.environ.get("LIVEKIT_API_KEY")
                          and os.environ.get("LIVEKIT_API_SECRET"))
        return {"status": "ok", "provider": provider.name, "livekit_configured": configured}

    @app.post("/rtc-token")
    async def rtc_token(request: Request):
        body = await request.json()
        meeting_id = body.get("meeting_id")
        identity = body.get("identity")
        if not meeting_id or not identity:
            return JSONResponse({"error_code": "BAD_REQUEST"}, status_code=400)
        try:
            provider.authorize(request, meeting_id, identity)
            credentials = issue_token(meeting_id, identity)
        except IdentityError as exc:
            return JSONResponse({"error_code": exc.code, "message": exc.message},
                                status_code=exc.status)
        except DemoError as exc:
            return JSONResponse({"error_code": exc.code, "message": exc.message},
                                status_code=exc.status)
        # Never log the token; it is a short-lived secret bound to the identity.
        return JSONResponse(credentials)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind loopback by default; public exposure needs TLS + real auth")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--provider", choices=["mock", "production"], default="mock")
    args = parser.parse_args()
    import uvicorn
    prov = ProductionIdentityProvider() if args.provider == "production" else MockIdentityProvider()
    uvicorn.run(create_token_service(prov), host=args.host, port=args.port,
                access_log=False, proxy_headers=False)
