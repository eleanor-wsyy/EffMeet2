# services/relay — 媒体中继服务

负责远程成员与现场设备之间的媒体流中继。

## 职责

- 设备通过 WebSocket 连接，发送 PCM 音频帧（s16le, 16kHz, mono, 20ms/frame）
- 中继远程音轨到控制器（HTTP POST）
- 接收控制器 TTS 音频并推送到设备
- 配对与 media-token 校验
- 不处理业务逻辑，只负责媒体传输

## 启动

```bash
# 默认监听 127.0.0.1:8766
python -m uvicorn services.relay.app:app --host 127.0.0.1 --port 8766
```

## 协议

WebSocket 端点：`/ws/audio/{session_id}?token=<media_token>&device_id=<device_id>`

1. 客户端发送 `AudioStreamConfig` JSON 帧
2. 服务端回复 `AudioStreamReady` JSON 帧
3. 客户端发送二进制 PCM 帧（640 bytes = 20ms）
4. 客户端发送 `AudioStreamEnd` JSON 帧结束

## 状态

骨架可运行，PCM 帧接收和转发逻辑待与控制器 ASR 管道对接。当前为 mock 模式，不验证 token。
