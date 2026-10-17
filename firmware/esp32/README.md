# firmware/esp32 — ESP32-S3 固件

机内音频、播放、Wi-Fi、转头与状态灯。

## 职责

- 拾音（机内麦克风）+ 音频前处理（AFE）
- 播放（扬声器）+ 独立停止
- Wi-Fi 连接与 PCM 音频流推送
- 单轴转头控制 + 状态灯
- 摄像头 JPEG 抓拍

## 技术栈

- ESP-IDF (C/C++)
- 板卡：ESP32-S3（具体型号待定）
- 音频编解码：板载 Codec（I2S 接口）

## 状态

**2026-10-16：已搭出 ESP-IDF 工程骨架（NOT-VERIFIED，未编译/未烧录/未上硬件）。**
模块状态表、开放集成点与契约对齐参照见 [docs/FIRMWARE_STATUS.md](docs/FIRMWARE_STATUS.md)。

- 工程树：`CMakeLists.txt` / `sdkconfig.defaults` / `partitions.csv` / `main/`（组件）。
- 已按仓库现有契约落地：EFMA 帧编解码（`main/efma_codec.c`，`protocol.py` 的 C 移植，纯 C 可主机测）、
  WebSocket 传输（`main/ws_transport.c`）、设备会话/命令/回执状态机（`main/device_session.c`）。
- 外设（I2S 拾音/播放、AFE/AEC、舵机、状态灯、摄像头）均为标注 `NOT_SUPPORTED` 的桩，引脚为占位。
- 本机无 ESP-IDF/gcc 工具链，**未编译**；唯一可独立验证的是 `test/test_efma_host.c`（需 gcc）。

当前 Demo 阶段音频走电脑伴侣应用（路线A），固件为最终形态（路线B）的核心。

## 关键约束

- 不承担 FunASR 或通用大模型推理
- 网络发送完成 ≠ 播报完成，需机内播放回执
- 舵机运动不引发复位
