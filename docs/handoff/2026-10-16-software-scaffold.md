# 2026-10-16 · 未完成软件部分搭框架（固件/LiveKit部署/实机验收 harness）

> 本次只**搭框架**，不声称任何实机/公网/硬件已通。所有新增外设与部署路径均标注
> NOT-VERIFIED / NOT_RUN，遵循"未验证项不得改写为 PASS/已完成"的纪律。
> 硬件打印/装配进度以 [hardware/robot-design/HANDOFF.md](../../hardware/robot-design/HANDOFF.md) 为准，本文只记软件。

## 背景：未完成软件项的终局目标

路线B 终局＝机器人脱离电脑、经 Wi-Fi 直连云端，独立完成
"真实采集 → ASR → 千问判断 → 本人网页确认 → 机器人实播 → 现场回应跟踪"闭环，
声学上能边播边听不误触发（真 AEC），远程成员手机/平板即可参会。
对照 [10-05 交接"未完成边界"](2026-10-05-final-handoff.md)：ESP32 固件、声学 AEC、
完整 LiveKit 链路+生产鉴权、连续真人实机验收。

## 本次新增（三块骨架）

### 1. ESP32-S3 固件工程骨架 — `firmware/esp32/`（NOT-VERIFIED，未编译/未烧录）
- ESP-IDF v5.x 工程树：`CMakeLists.txt`/`sdkconfig.defaults`/`partitions.csv`/`main/`。
- **EFMA 帧编解码** `main/efma_codec.{h,c}`：`services/relay/protocol.py` 的逐字段 C 移植，
  纯 C 无 ESP 依赖（可主机编译）。附 `test/test_efma_host.c`（需 gcc）。
- **WebSocket 传输** `main/ws_transport.{h,c}`：`/device/v1/audio`＋`/device/v1/playback`，
  Bearer 头鉴权（不走 URL/Origin，对齐 `media.py`）。
- **设备会话/状态机** `main/device_session.{h,c}`：配对/DeviceHello、上行流、播放握手
  （audio.start→ready→accepted→started→帧+ack→audio.end→completed→playback.closed）、
  RobotCommand 分发（orient/light/speak/stop）、RobotReceipt 状态机。
- 外设桩（均 `ESP_ERR_NOT_SUPPORTED`）：I2S 拾音(INMP441)/播放(MAX98357A)、AFE/AEC、
  舵机(MG90S 2:1→±45°)、状态灯(WS2812)、摄像头 JPEG。引脚为占位。
- 模块状态表/开放集成点/契约参照见 [firmware/esp32/docs/FIRMWARE_STATUS.md](../../firmware/esp32/docs/FIRMWARE_STATUS.md)。
- **开放集成点**：命令下发通道（建议订阅控制器 events WS 过滤本 device_id 的 command.queued）、
  Wi-Fi 配网、media_token 入 NVS、真 AEC、引脚/电气核对。

### 2. LiveKit 公网部署骨架 — `deploy/livekit/`（NOT-VERIFIED，未部署）
- `token_service.py`：复用既有 `livekit_token.issue_token`（不重复 JWT 逻辑），前置
  `IdentityProvider` 鉴权缝。`MockIdentityProvider` 复刻台架（仅合成 remote_1/2）；
  `ProductionIdentityProvider` 为桩，未接真实账号前抛 501。
- `gateway.env.example`（无密钥模板）、`livekit.yaml`（server 配置模板）、
  `docker-compose.yml`（livekit-server+redis+TURN）。
- 说明与 bring-up 步骤见 [deploy/livekit/README.md](../../deploy/livekit/README.md)。

### 3. 连续实机验收 harness — `tests/acceptance/`（默认 NOT_RUN）
- `harness.py`：把链拆成 S1..S6 阶段，两种模式。`mock` 用合成 ASR/TTS/模型驱动**真实**
  控制器+relay 软件证明接线（状态 `MOCK_OK`，**绝不** PASS）；`real` 按真实依赖门控，
  缺依赖→`NOT_RUN`，满足后须凭证据才 `PASS`（真实执行路径目前是 bring-up 任务，仍报 NOT_RUN）。
- `mock_chain.py`：跑通 S1→S6（上行→ASR→分析→本人确认→播放 completed→观点地图）。
- `test_e2e_acceptance.py`：mock 接线证明 + real 无门槛必 NOT_RUN + 实机门控（skipUnless）。
- 逐项打勾清单 [acceptance_checklist.md](../../tests/acceptance/acceptance_checklist.md)（全 NOT_RUN）。
- 与 `tests/test_bench.py` 区别：bench 是合成协议回归；本 harness 是验收粒度编排+阶段证据+实机门控。

## 验证证据（本机可跑部分）

- 全量单测：`python -m unittest discover -s tests` → **106 tests OK（skipped=1）**；
  含原 102 项无回归 + 新增 4 项验收 harness（1 项实机门控 skip）。
- 验收 harness mock 链路：S1→S6 跑通，S5 播放命令终态 `completed`、ack 2 帧。
- EFMA C 编解码：本机无 gcc/idf 不能编译 C；以**逐行转写 fuzz** 对照 `protocol.py`，
  **74105 次校验 0 不一致**（含解码字节、ok/duplicate/gap 诊断、精确错误码）。
  C 与转写间的笔误风险由 `test/test_efma_host.c`（有 gcc 处可跑）兜底。
- 未验证：固件未编译/未烧录；LiveKit 未部署/未签真实 token；实机 S1/S5 等未跑。

## 纪律与边界

- 密钥仅走环境变量/NVS，不入代码、日志、提交、URL。
- mock/台架结果不构成实机验收；NOT_RUN/NOT-VERIFIED 不得改写成 PASS。
- 本次未改动任何既有源码（仅新增文件 + relay README 一处指针），无回归。
