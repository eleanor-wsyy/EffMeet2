"""EffMeet2 continuous real-machine acceptance harness (tests/acceptance).

End-to-end chain the 2026-10-05 handoff lists as NOT accepted:
  真实采集 -> ASR -> 千问判断 -> 本人网页确认 -> 机器人实播 -> 现场回应跟踪

Two modes:
  - mock : drives the real controller/relay software with synthetic ASR/TTS/model
           to PROVE THE HARNESS WIRING. Stage status is MOCK_OK, never PASS.
           (Synthetic protocol regression already lives in tests/test_bench.py;
           this is acceptance-granularity orchestration, not a duplicate.)
  - real : each stage is gated on its real dependency (mic/FunASR/qwen/web owner/
           robot speaker/onsite mic). Missing dependency -> NOT_RUN with a reason.
           A stage may only report PASS after its real pass-criteria is evidenced.

Discipline: mock never yields PASS; real never yields PASS without evidence.
This mirrors the repo rule that unverified items are not rewritten as PASS/done.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

MOCK_OK = "MOCK_OK"
NOT_RUN = "NOT_RUN"
PASS = "PASS"
FAIL = "FAIL"


@dataclass
class Stage:
    stage_id: str
    name: str
    requires: list[str]          # real dependency keys (see REAL_GATES)
    pass_criteria: str


@dataclass
class StageResult:
    stage_id: str
    status: str                  # MOCK_OK | NOT_RUN | PASS | FAIL
    reason: str = ""
    evidence: dict = field(default_factory=dict)


# Ordered chain. pass_criteria is what a real run must evidence before PASS.
STAGES: list[Stage] = [
    Stage("S1_capture", "真实采集：机内麦/浏览器录音 -> 16kHz mono s16le PCM",
          ["microphone"], "真人语音录成合规 WAV/PCM，时长与电平可核"),
    Stage("S2_asr", "FunASR 离线转写 -> UtteranceFinal 入账",
          ["funasr"], "转写文本非空且可定位到发言；ASR 服务真实可达"),
    Stage("S3_analyze", "qwen-plus 判断 status + 证据引用 -> 候选",
          ["qwen"], "真实模型返回 status∈{uncertain,possibly_unresponded,responded} 且证据 ID 合法"),
    Stage("S4_confirm", "观点本人网页确认 -> 命令 queued",
          ["web_owner"], "由观点所有者本人在网页确认；非本人/过期/上下文变更被拒"),
    Stage("S5_playback", "机器人实播 -> RobotReceipt accepted/started/completed",
          ["robot_speaker"], "设备真实出声并回 completed 回执；网络发完≠播完"),
    Stage("S6_response_tracking", "现场回应跟踪 -> 观点地图 response_status 更新",
          ["onsite_mic"], "现场回应被采集并核对，观点地图 response_status 随之更新"),
]

# A real gate is satisfied only when its env var is set to a truthy value AND,
# for hardware stages, a physical device is attested. Absent -> NOT_RUN.
REAL_GATES = {
    "microphone": "EFFMEET_ACC_MIC",
    "funasr": "FUNASR_WS_URL",
    "qwen": "QWEN_API_KEY",
    "web_owner": "EFFMEET_ACC_WEB_OWNER",
    "robot_speaker": "EFFMEET_ACC_ROBOT",
    "onsite_mic": "EFFMEET_ACC_ONSITE_MIC",
}


def _gate_missing(dep: str) -> str | None:
    """Return a NOT_RUN reason if the real dependency is unavailable, else None."""
    var = REAL_GATES[dep]
    if not os.environ.get(var):
        return f"NOT_RUN: 缺真实依赖 {dep}（设 {var} 并确保硬件/服务就绪后重跑）"
    return None


class E2EAcceptanceHarness:
    def __init__(self, mode: str = "mock"):
        if mode not in {"mock", "real"}:
            raise ValueError("mode must be 'mock' or 'real'")
        self.mode = mode
        self.results: list[StageResult] = []

    # ---- public API ----
    def run(self) -> list[StageResult]:
        self.results = []
        if self.mode == "mock":
            self._run_mock()
        else:
            self._run_real()
        return self.results

    def summary(self) -> dict[str, str]:
        return {r.stage_id: r.status for r in self.results}

    # ---- mock mode: prove wiring against the real software stack ----
    def _run_mock(self) -> None:
        from .mock_chain import run_mock_chain
        evidence_by_stage = run_mock_chain()
        for stage in STAGES:
            ev = evidence_by_stage.get(stage.stage_id, {})
            # MOCK_OK means the software chain executed; it is NOT real acceptance.
            self.results.append(StageResult(stage.stage_id, MOCK_OK,
                                            reason="mock 链路跑通（非实机验收）", evidence=ev))

    # ---- real mode: gate each stage; never PASS without evidence ----
    def _run_real(self) -> None:
        from . import real_chain
        context: dict = {}
        handlers = {"S1_capture": real_chain.capture, "S2_asr": real_chain.asr,
                    "S3_analyze": real_chain.analyze,
                    "S6_response_tracking": real_chain.response_tracking}
        for stage in STAGES:
            missing = None
            for dep in stage.requires:
                missing = _gate_missing(dep)
                if missing:
                    break
            if missing:
                self.results.append(StageResult(stage.stage_id, NOT_RUN, reason=missing))
                continue
            handler = handlers.get(stage.stage_id)
            if handler is None:
                self.results.append(StageResult(
                    stage.stage_id, NOT_RUN,
                    reason="NOT_RUN: 真实执行路径未实现（bring-up 任务）；门槛已满足但不得伪报 PASS"))
                continue
            try:
                evidence = handler(context)
            except real_chain.NotRun as exc:
                self.results.append(StageResult(stage.stage_id, NOT_RUN,
                                                reason=f"NOT_RUN: {exc}"))
            except Exception as exc:
                self.results.append(StageResult(
                    stage.stage_id, FAIL,
                    reason=f"FAIL: {type(exc).__name__}: {exc}"))
            else:
                self.results.append(StageResult(stage.stage_id, PASS,
                                                reason="真实链路通过（证据见 evidence）",
                                                evidence=evidence))
