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

**2026-10-19 起，S1/S2 的真实执行路径已实现**（`real_chain.py`）：

- S1：`EFFMEET_ACC_MIC` 设为真实 16 kHz mono WAV 路径，或设为 `1` 用
  `sounddevice` 录默认麦克风（秒数由 `EFFMEET_ACC_MIC_SECONDS` 控制，默认 3 秒）。
  只接受 0.2–30 秒、非静音（≥ -50 dBFS）的 PCM；失败记 `FAIL`，不是 `PASS`。
- S2：把 S1 的 PCM 通过真实 `/device/v1/audio` WebSocket 送入真实控制器，
  由真实 `FunASR` 转写并落账；返回 `utterance.final` 才算通过。
- **S3 真实路径已实现**（`real_chain.analyze`）：真实 `qwen-plus`；2026-10-19 实测返回
  `uncertain` 并正确不生成候选。Key 只从 `QWEN_API_KEY` 环境变量读取。
- S4/S5 仍只报 `NOT_RUN`：S4 需要真实账号，S5 需要机器人。
- **S6 真实路径已实现**（`real_chain.response_tracking`）：现场音频走真实 media WS +
  真实 FunASR，回应核对与观点地图走真实控制器；候选分析用本地 stub、本人确认用
  `remote_1` 测试身份，因此证据里明确标注“不是完整人工验收”。
- 2026-10-19 联合运行：同一 real harness 设置 S1/S2/S3/S6 门槛，结果为
  **S1/S2/S3/S6 PASS，S4/S5 NOT_RUN**（缺真实账号/机器人）。
- **2026-10-19 实测**：本地 `.venv-asr` 的 SenseVoiceSmall 就绪后，
  `EFFMEET_ACC_MIC=data/acceptance_speech.wav FUNASR_WS_URL=ws://127.0.0.1:10096`
  跑出 `S1_capture PASS` + `S2_asr PASS`；转写文本非空并带 `utterance_id`。
  输入是 TTS 合成语音，不是真人录音，因此“真人录音”验收项仍不勾选。
- 远程音轨路径另见 `scripts/smoke_livekit_remote_asr.py`：`remote_1` 发布 TTS 音轨，
  relay 订阅后由真实 SenseVoiceSmall 入账（`channel=remote`），2026-10-19 实测 PASS。

## 运行

```powershell
# mock 接线证明（无需硬件/密钥）
.\.venv\Scripts\python.exe -m unittest tests.acceptance.test_e2e_acceptance -v

# 只跑 S1/S2（不需要百炼 Key、不需要机器人）：
$env:EFFMEET_ACCEPTANCE_REAL = "1"
$env:EFFMEET_ACC_MIC = "C:\path\to\real-16k-mono.wav"  # 或 "1" 用默认麦克风
$env:EFFMEET_ACC_MIC_SECONDS = "3"                     # 仅 EFFMEET_ACC_MIC=1 时生效
$env:FUNASR_WS_URL = "ws://127.0.0.1:10096"
.\.venv\Scripts\python.exe -m unittest tests.acceptance.test_e2e_acceptance -v

# 备齐真实账号/模型/机器人后，再打开 S3–S6 的门槛：
$env:QWEN_API_KEY = "sk-..."; $env:EFFMEET_ACC_WEB_OWNER = "1"
$env:EFFMEET_ACC_ROBOT = "1"; $env:EFFMEET_ACC_ONSITE_MIC = "1"
```

## 纪律

- `mock` 永远不产 `PASS`；`real` 没有证据不产 `PASS`。
- S1/S2 的真实执行路径已实现；没有真实麦克风/ASR 证据时仍只报 `NOT_RUN`/`FAIL`，不得伪报 PASS。
- S4/S5 的真实执行路径仍是 **bring-up 任务**（真实账号/机器人）：门槛满足也只报
  `NOT_RUN: 真实执行路径未实现`。逐项打勾见 [acceptance_checklist.md](acceptance_checklist.md)。
- 密钥仅走环境变量，不入代码/日志/提交。
