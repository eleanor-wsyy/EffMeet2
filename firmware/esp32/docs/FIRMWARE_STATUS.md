# ESP32-S3 固件骨架状态（NOT-VERIFIED）

> 本目录是 2026-10-16 搭出的**可编译目标工程骨架**，用于把仓库里已有的精确契约
> （EFMA 帧格式、RobotCommand/RobotReceipt、AudioStreamConfig/Ready/End、DeviceHello、
> 设备配对/media_token）落到固件侧。**本机无 ESP-IDF/gcc 工具链，未编译、未烧录、未上硬件。**
> 所有外设路径均为清晰标注的桩，返回 `ESP_ERR_NOT_SUPPORTED`，不得据此声称任何硬件已通。

## 终局目标（路线B）

机器人脱离电脑、经 Wi-Fi 直连云端，独立完成：机内麦拾音 → AFE/AEC 前处理 →
Wi-Fi 推 PCM（EFMA 帧）→ 收 `speak` 命令实播并回**播放完成回执**（网络发完≠播完）→
单轴转头 + 状态灯 + 摄像头 JPEG 抓拍。声学上能**边播边听**不误触发（真 AEC）。

## 模块状态表

| 模块 | 文件 | 状态 | 说明 |
|---|---|---|---|
| EFMA 帧编解码 | `main/efma_codec.{h,c}` | 逻辑完成，**未在设备链路验证** | `protocol.py` 的逐字段 C 移植；纯 C 无 ESP 依赖，可主机编译。附 `test/test_efma_host.c` |
| WebSocket 传输 | `main/ws_transport.{h,c}` | 桩，未编译 | `esp_websocket_client` 封装；Bearer 头鉴权（不走 URL/Origin，对齐 `media.py`） |
| 设备会话/协议状态机 | `main/device_session.{h,c}` | 结构完成，未编译 | 配对/Hello、上行流、播放握手、回执状态机、命令分发 |
| 拾音 I2S(INMP441) | `main/audio_capture.{h,c}` | 桩 NOT_SUPPORTED | 引脚为占位，须与 `hardware/electronics` 接线核对 |
| 播放 I2S(MAX98357A) | `main/audio_playback.{h,c}` | 桩 NOT_SUPPORTED | 持有"播完"边界，gate `RobotReceipt(completed)` |
| AEC/AFE | `main/aec_afe.{h,c}` | 桩 NOT_SUPPORTED | ESP-SR AFE 接入点；`quiet_moment()` 当前仅软件互斥代理，**非校准 VAD/AEC** |
| 转头舵机(MG90S) | `main/servo_yaw.{h,c}` | 桩 NOT_SUPPORTED | 2:1 减速→头±45°；限位/减速比未确认 |
| 状态灯(WS2812) | `main/status_led.{h,c}` | 桩 NOT_SUPPORTED | pattern=idle/notice/error/off；色序未确认 |
| 摄像头抓拍 | `main/camera_capture.{h,c}` | 桩 NOT_SUPPORTED | 型号/引脚 TBD |
| 启动序列 | `main/main.c` | 桩，未编译 | NVS→Wi-Fi→载配对身份→外设 init→会话任务 |

## 已知开放集成点（bring-up 必做）

1. **命令下发通道**：本地台架由主机侧驱动播放器；真机器人需要一条把 `queued` 的
   `command_id` 送到设备的通道（建议订阅控制器 events WS，过滤本 device_id 的
   `robot command.queued`）。`device_session_on_command()` 是接入缝，传输未接。
2. **Wi-Fi 配网**：当前用 Kconfig 编译期 SSID/口令，应改为 softAP/blufi/NVS 运行时配网。
3. **media_token 入 NVS**：operator 先 `POST /api/v1/meetings/{mid}/devices/{device_id}/pair`
   拿到 token，再provision 进设备 NVS（命名空间 `effmeet`，键 `meeting_id`/`media_token`）。
   token 有效期 1 小时（`bench.authenticate`），过期需重新配对。**密钥不入库、不打日志。**
4. **真 AEC**：`aec_afe` 需接 ESP-SR AFE 的回声参考通道 + 延迟对齐 + 双讲，替换软件互斥代理。
5. **引脚/电气核对**：`app_config.h` 全部 GPIO 为占位，须与最终板型和电气 BOM 对齐。

## 契约对齐参照（仓库内真源）

- 帧格式：`services/relay/protocol.py`（`!4sBBHIIII`，24 字节头，640 字节/20ms 载荷）
- 媒体流：`services/relay/media.py`（`/device/v1/audio`、`/device/v1/playback`、SAFE_PAUSE_REQUIRED）
- 命令/回执/Hello/音频配置：`contracts/v1/bundle.json`（RobotCommand / RobotReceipt / DeviceHello / AudioStream*）
- 配对/token：`services/controller/store.py: pair_device`、`services/controller/app.py: pair_device`

## 验证边界

- 本环境**不能**编译 ESP-IDF 工程（无 `idf.py`），也**不能**主机编译 C（无 gcc）。
- 唯一可独立验证的是 EFMA 编解码逻辑：`test/test_efma_host.c` 在有 gcc 的机器上可跑，
  断言与 `protocol.py` 行为一致（重复帧/错流/间隙隐藏/间隙过大/序列非法/短头）。
- 其余模块的"完成"仅指接口与协议形状对齐，**不代表任何硬件或链路已验收**。
