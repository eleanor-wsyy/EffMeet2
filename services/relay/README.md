# services/relay — 本机音频台架

当前媒体路由和控制器共用一个进程、一个账本。原独立中继骨架已替换；不再通过 `EFFMEET_CONTROLLER_URL` 转发。

## 启动与验收

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe scripts/run_bench.py
# 自行启动临时服务的合成网络闭环，不需先启动台架
.\.venv\Scripts\python.exe scripts/smoke_bench.py
```

推荐入口默认 [127.0.0.1:8768](http://127.0.0.1:8768)。`scripts/run_relay.py` 仍可在 8766 启动统一台架兼容入口，但不是需要另外启动的独立媒体进程；不要让两个进程共用数据库。

## 当前协议

- 上行：`WS /device/v1/audio`；播放：`WS /device/v1/playback`。
- 通过 `Authorization: Bearer ...` 发送配对凭据，只接受回环本机客户端；不接受 URL 查询参数或浏览器 Origin。
- 上行需先通过主持人 HTTP 接口建立设备配对与会议/流/来源绑定，再发 `AudioStreamConfig`，收到 `AudioStreamReady` 后发送二进制帧。
- 帧头 24 字节，格式 `!4sBBHIIII`；有效载荷 16kHz mono s16le，典型 20ms/320 个采样/640 字节。典型总帧长为 **664 字节**，末帧可更短。
- `audio.end` 后调用 FunASR offline 接口；单段最多 30 秒，非实时分段 ASR。
- 下行先验证已确认的当前命令，发送 start/ready，再逐帧等待 `audio.ack`；最多一个 20ms 帧未 ACK。只有设备报告排空完成才接受 completed。
- 停止取消待播内容；断连或重启不自动重播。音频发送结束不代表实际播放结束。

旧 `/ws/audio/{session_id}?token=...` 和 `/api/tts/{session_id}` 已移除。ACK、播放器首条 JSON 与 `/api/bench/*` 是本机台架扩展，尚未纳入正式契约。

## 文件与边界

`protocol.py` 管帧格式；`asr.py` 对接 FunASR；`tts.py` / `synthesize.ps1` 生成 Windows PCM；`media.py` 负责受控收发与回执。配置缺失时明确报错。

已验证真实网络 + 合成服务闭环，以及 Windows TTS 格式。真实 ASR、千问、音频设备、ESP32、LiveKit、AEC/双讲尚未验收。`--simulate` 是模拟音频汇，不发声。

完整命令、配置、接口表和复现方法见 [10 月 5 日交接记录](../../docs/handoff/2026-10-05.md)。
