"""No ASR, LLM, TTS, sound playback or physical device calls in these adapters."""
from uuid import uuid4

from .contracts import DemoError


class FakeAnalyzer:
    mode = "mock"

    def analyze(self, evidence, status):
        remote = [x for x in evidence if x["channel"] == "remote"]
        owners = {x["speaker_id"] for x in remote}
        if not remote or None in owners or len(owners) != 1:
            raise DemoError(422, "OWNER_UNCLEAR", "请选择归属明确的同一线上成员的发言。")
        responses = [x["utterance_id"] for x in evidence if x["channel"] == "onsite"]
        if status == "responded" and not responses:
            raise DemoError(422, "RESPONSE_MISSING", "模拟已回应场景需包含一条现场回应。")
        # This is intentionally a selected scenario, NOT semantic detection.
        snippet = remote[-1]["text"].strip()[:42].rstrip("。！？!?.,，；;")
        text = "线上成员提出：" + snippet + "，现场可以回应一下吗？"
        return {
            "claim_id": str(uuid4()),
            "owner_speaker_id": next(iter(owners)),
            "status": status,
            "evidence_ids": [x["utterance_id"] for x in evidence],
            "response_utterance_ids": responses if status == "responded" else [],
            "proposed_text": text,
            "reason": "本地手选模拟场景：" + {
                "possibly_unresponded": "线上观点可能尚未获得现场回应",
                "responded": "线上观点已有现场回应",
                "uncertain": "线上观点是否获得现场回应不确定",
            }[status] + "；未调用真实模型，不作语义判断。",
            "model": {"provider": "mock", "model_id": "fake-analyzer", "prompt_version": "mock-v1"},
        }


class FakeRobot:
    mode = "mock"
    device_id = "fake_robot"

    def __init__(self, fail=False):
        self.boot_id = str(uuid4())
        self.fail = fail
        self.calls = []

    def execute(self, command):
        if command["action"] != "speak" or command["target_device_id"] != self.device_id:
            raise DemoError(422, "UNSUPPORTED_ACTION", "模拟设备只接收本机speak。")
        self.calls.append(command["command_id"])
        statuses = ["accepted", "failed"] if self.fail else ["accepted", "started", "completed"]
        return [
            {
                "command_id": command["command_id"],
                "target_device_id": self.device_id,
                "boot_id": self.boot_id,
                "status": status,
                "error_code": "MOCK_DEVICE_FAILURE" if status == "failed" else None,
            }
            for status in statuses
        ]
