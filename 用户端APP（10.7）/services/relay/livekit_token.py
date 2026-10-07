"""LiveKit token 签发（服务端持有密钥，前端只拿一次性 token）。

由小W（A 侧助手）代做 2026-10-06，配合 LiveKit 最小实现任务
（docs/handoff/2026-10-06-livekit最小实现任务.md）。房间名 = meeting_id；
远程成员只能发布自己的麦克风轨，token 与身份绑定。
"""
import os
import time

from ..controller.contracts import DemoError


def issue_token(meeting_id, identity, *, relay=False):
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    url = os.environ.get("LIVEKIT_URL")
    if not api_key or not api_secret or not url:
        raise DemoError(503, "LIVEKIT_NOT_CONFIGURED",
                        "LiveKit 未配置：服务端需 LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET。")
    if not isinstance(identity, str) or not identity.strip():
        raise DemoError(422, "IDENTITY_REQUIRED", "缺少成员标识。")
    try:
        import jwt
    except ImportError:
        raise DemoError(500, "PYJWT_MISSING", "服务端缺依赖：pip install pyjwt")
    now = int(time.time())
    payload = {
        "iss": api_key,
        "sub": identity.strip(),
        "nbf": now - 10,
        "exp": now + 3600,
        "video": {"roomJoin": True, "room": meeting_id, "canPublish": not relay,
                  "canSubscribe": True, "canPublishData": False, "canUpdateOwnMetadata": False},
    }
    if not relay:
        payload['video']['canPublishSources'] = ['microphone']
    return {"token": jwt.encode(payload, api_secret, algorithm="HS256"), "url": url, "room": meeting_id}
