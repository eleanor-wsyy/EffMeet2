# 连续实机验收 harness（tests/acceptance）

> 2026-10-16 搭出。对应 10-05 交接里**未完成**的"实时采集 → ASR → 千问 → 本人网页确认 →
> 机器人实播 → 现场回应跟踪"连续实机验收。本 harness 把这条链拆成 6 个可独立门控的阶段，
> **默认 NOT_RUN**，绝不把未验证项伪报成 PASS。

## 两种模式

| 模式 | 作用 | 阶段状态 | 是否需硬件 |
|---|---|---|---|
| `mock` | 用合成 ASR/TTS/模型驱动**真实**控制器+relay 软件，证明 harness 接线正确 | `MOCK_OK`（**非** PASS） | 否，CI 可跑 |
| `real` | 每阶段按真实依赖门控；缺依赖→`NOT_RUN`；满足后须凭证据才 `PASS` | `NOT_RUN`/`PASS`/`FAIL` | 是 |

`mock` 与 `tests/test_bench.py` 的区别：bench 是合成协议回归（帧/会话/回执细节），
本 harness 是**验收粒度的端到端编排**＋阶段证据采集＋实机门控，不重复 bench 的断言。

## 阶段与真实门槛

| 阶段 | 名称 | 真实依赖（env 门槛） | PASS 判据 |
|---|---|---|---|
| S1_capture | 真实采集→16k mono PCM | `EFFMEET_ACC_MIC` | 真人语音录成合规 WAV/PCM，时长电平可核 |
| S2_asr | FunASR 离线转写→入账 | `FUNASR_WS_URL` | 转写非空且可定位发言；ASR 真实可达 |
| S3_analyze | qwen-plus 判断→候选 | `QWEN_API_KEY` | 真实模型返回合法 status + 证据 ID |
| S4_confirm | 本人网页确认→queued | `EFFMEET_ACC_WEB_OWNER` | 观点所有者本人确认；非本人/过期/上下文变更被拒 |
| S5_playback | 机器人实播→completed 回执 | `EFFMEET_ACC_ROBOT` | 设备真实出声并回 completed；网络发完≠播完 |
| S6_response_tracking | 现场回应跟踪→观点地图 | `EFFMEET_ACC_ONSITE_MIC` | 现场回应被采集核对，response_status 随之更新 |

## 运行

```powershell
# mock 接线证明（无需硬件/密钥）
.\.venv\Scripts\python.exe -m unittest tests.acceptance.test_e2e_acceptance -v

# 实机验收（备齐硬件+FunASR+qwen+LiveKit 后）
$env:EFFMEET_ACCEPTANCE_REAL = "1"
$env:EFFMEET_ACC_MIC = "1"; $env:FUNASR_WS_URL = "ws://127.0.0.1:10096"
$env:QWEN_API_KEY = "sk-..."; $env:EFFMEET_ACC_WEB_OWNER = "1"
$env:EFFMEET_ACC_ROBOT = "1"; $env:EFFMEET_ACC_ONSITE_MIC = "1"
.\.venv\Scripts\python.exe -m unittest tests.acceptance.test_e2e_acceptance -v
```

## 纪律

- `mock` 永远不产 `PASS`；`real` 没有证据不产 `PASS`。
- 真实执行路径（S1 真麦、S5 真机器人出声等）目前是 **bring-up 任务**：门槛满足也只报
  `NOT_RUN: 真实执行路径未实现`，不得伪报 PASS。逐项打勾见 [acceptance_checklist.md](acceptance_checklist.md)。
- 密钥仅走环境变量，不入代码/日志/提交。
