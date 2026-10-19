# ESP32-S3 固件骨架状态（ESP-IDF 已编译，未烧录）

> 本目录是 2026-10-16 搭出的**可编译目标工程骨架**，用于把仓库里已有的精确契约
> （EFMA 帧格式、RobotCommand/RobotReceipt、AudioStreamConfig/Ready/End、DeviceHello、
> 设备配对/media_token）落到固件侧。**2026-10-19 已用 ESP-IDF v5.4.1 编译通过；
> 未烧录、未上硬件。**
> 所有外设路径均为清晰标注的桩，返回 `ESP_ERR_NOT_SUPPORTED`，不得据此声称任何硬件已通。

## 终局目标（路线B）

机器人脱离电脑、经 Wi-Fi 直连云端，独立完成：机内麦拾音 → AFE/AEC 前处理 →
Wi-Fi 推 PCM（EFMA 帧）→ 收 `speak` 命令实播并回**播放完成回执**（网络发完≠播完）→
单轴转头 + 状态灯 + 摄像头 JPEG 抓拍。声学上能**边播边听**不误触发（真 AEC）。

## 模块状态表

| 模块 | 文件 | 状态 | 说明 |
|---|---|---|---|
| EFMA 帧编解码 | `main/efma_codec.{h,c}` | **主机测试通过（2026-10-19）**，未在设备链路验证 | `protocol.py` 的逐字段 C 移植；纯 C 无 ESP 依赖。`scripts/test_efma_host.py` 用 ziglang 编译并运行 `test/test_efma_host.c`，全部断言通过 |
| WebSocket 传输 | `main/ws_transport.{h,c}` | 编译通过，未在设备链路验证 | `esp_websocket_client` 封装；Bearer 头鉴权（不走 URL/Origin，对齐 `media.py`） |
| 设备会话/协议状态机 | `main/device_session.{h,c}` | 编译通过，未在设备链路验证 | 配对/Hello、上行流、播放握手、回执状态机、命令分发 |
| 拾音 I2S(INMP441) | `main/audio_capture.{h,c}` | 桩 NOT_SUPPORTED | 引脚为占位，须与 `hardware/electronics` 接线核对 |
| 播放 I2S(MAX98357A) | `main/audio_playback.{h,c}` | 桩 NOT_SUPPORTED | 持有"播完"边界，gate `RobotReceipt(completed)` |
| AEC/AFE | `main/aec_afe.{h,c}` | 桩 NOT_SUPPORTED | ESP-SR AFE 接入点；`quiet_moment()` 当前仅软件互斥代理，**非校准 VAD/AEC** |
| 转头舵机(MG90S) | `main/servo_yaw.{h,c}` | 桩 NOT_SUPPORTED | 2:1 减速→头±45°；限位/减速比未确认 |
| 状态灯(WS2812) | `main/status_led.{h,c}` | 桩 NOT_SUPPORTED | pattern=idle/notice/error/off；色序未确认 |
| 摄像头抓拍 | `main/camera_capture.{h,c}` | 桩 NOT_SUPPORTED | 型号/引脚 TBD |
| 启动序列 | `main/main.c` | 编译通过，未在设备链路验证 | NVS→Wi-Fi→载配对身份→外设 init→会话任务 |

## 构建依赖（2026-10-19）

- 工具链：ESP-IDF **v5.4.1**（`.local/esp-idf`，未入仓），target `esp32s3`。
- `main/idf_component.yml`：`esp_websocket_client`（WS 传输）、`led_strip`（状态灯）、
  `esp-sr`（AFE/AEC，条件启用）。
- 生成物 `firmware/esp32/sdkconfig`、`build/`、`managed_components/` 已加入 `.gitignore`。
- 构建脚本：`scripts/build_firmware.ps1`（清除 `MSYSTEM`、固定 ESP-IDF Python 3.12
  环境、加载 `export.ps1`、`idf.py set-target esp32s3 build`）。只编译，不烧录。
- `sdkconfig.defaults` 假定 **8MB flash**（原 2MB 默认放不下 3.1MB 分区表）；
  最终板型/Flash 容量仍需以实物为准。
- **2026-10-19 编译结果**：`Project build complete`；
  `effmeet2_robot.bin` = 0xbfbf0（约 767KB），app 分区 3MB，剩余 75%；
  bootloader = 0x5220（36% free）。
- `idf.py size`：Flash Code 562,650 B + Flash Data 107,060 B；DIRAM 114,751/341,760 B
  （33.6%）；**IRAM 16,383/16,384 B（99.99%，仅剩 1 B）**。当前链接通过，但后续
  新增 IRAM 代码/中断会很容易溢出，需优先放 flash 或调整配置。
- 编译期修正：`esp_websocket_register_events`（1.8.0 API）、`PRIx32` 格式符、
  8MB flash、补 `esp_websocket_client` 组件依赖。
- `dependencies.lock` 已生成（esp-sr 1.9.5 / esp_websocket_client 1.8.0 /
  led_strip 2.5.5 / esp-dsp 1.4.12）。
- **未烧录、未上硬件**；外设仍为桩。

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

- ESP-IDF v5.4.1 工程已在本机**编译通过**（`scripts/build_firmware.ps1`）；未烧录、
  未连接设备，外设桩与外设链路仍未验证。
- EFMA 编解码已用可选 `ziglang` 编译器主机编译并通过：`scripts/test_efma_host.py` 输出
  `EFMA host tests passed (protocol.py parity)`，覆盖重复帧/错流/间隙隐藏/间隙过大/序列非法/短头。
  这是**主机逻辑验证**，不是设备链路验证。
- 其余模块的"完成"仅指接口与协议形状对齐，**不代表任何硬件或链路已验收**。
