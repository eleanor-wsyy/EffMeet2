# ESP32-S3 固件骨架状态（已烧录并启动，灯/舵机/I2S 音频已实现）

> 本目录是 2026-10-16 搭出的**可编译目标工程骨架**，用于把仓库里已有的精确契约
> （EFMA 帧格式、RobotCommand/RobotReceipt、AudioStreamConfig/Ready/End、DeviceHello、
> 设备配对/media_token）落到固件侧。**2026-10-20 已用 ESP-IDF v5.4.1 编译并烧录到
> 实机，启动通过；未配对时进入串口配网 REPL。**
> 已实现外设：WS2812 状态灯（GPIO48）、MG90S 舵机（GPIO38 LEDC）、
> I2S 拾音（INMP441）与 I2S 播放（MAX98357A）。**I2S 引脚仍为占位，须用 REPL
> `mic` / `tone` 命令对实机接线核对**；AFE/AEC 与摄像头仍为桩。

## 实机验证（2026-10-20）

- ESP32-S3 N16R8（16MB Flash + 8MB PSRAM），CH340 COM3。
- 烧录 954,880 B → 1,007,4xx B（视版本），Hash verified。
- 启动正常；未配对进入 `effmeet>` 配网 REPL。
- `provision_status` 返回“NVS namespace not found”（证明 NVS/REPL 可用）。
- `led notice/error/idle/off` 通过 REPL 切换，无错误。
- 舵机 LEDC 初始化无错误；未执行转头动作。
- **I2S 链路 DMA/时钟已验证**：`i2srate` 实测 rx=49/s、tx=50/s 描述符完成率
  （理论 50/s）；`mic` 50/50 帧读通（rms=0，因 INMP441 未接到占位引脚）；
  `tone 880 500` 25 帧全部写入无丢帧（MAX98357A 未接，无声属预期）。
  踩坑记录：`i2s_channel_read/write` 的 timeout 参数是**毫秒**不是 ticks，
  误传 `pdMS_TO_TICKS()` 会导致超时缩短 10 倍（FreeRTOS_HZ=100），表现为
  周期性 ESP_ERR_TIMEOUT。
- REPL 诊断命令：`mic`（采 1s 打印 RMS/peak/ISR 计数）、`tone [freq] [ms]`
  （正弦试音）、`i2srate`（测 1s 内 DMA 完成率）。ISR/溢出计数器保留在
  `audio_capture`/`audio_playback` 里作 bench 诊断。

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
| 拾音 I2S(INMP441) | `main/audio_capture.{h,c}` | **已实现，DMA/时钟实机验证（2026-10-20）** | 16 kHz 单声道，32-bit slot 截 s16（>>16）；引脚为占位，须与 `hardware/electronics` 接线核对后用 REPL `mic` 复测 |
| 播放 I2S(MAX98357A) | `main/audio_playback.{h,c}` | **已实现，DMA/时钟实机验证（2026-10-20）** | 持有"播完"边界，gate `RobotReceipt(completed)`；AMP_ENABLE(GPIO18) 门控；引脚占位待核对，`tone` 复测 |
| AEC/AFE | `main/aec_afe.{h,c}` | 桩 NOT_SUPPORTED | ESP-SR AFE 接入点；`quiet_moment()` 当前仅软件互斥代理，**非校准 VAD/AEC** |
| 转头舵机(MG90S) | `main/servo_yaw.{h,c}` | 已实现 LEDC，未实机验证 | 2:1 减速→头±45°；限位/减速比未确认 |
| 状态灯(WS2812) | `main/status_led.{h,c}` | 已实现 led_strip，未实机验证 | pattern=idle/notice/error/off；色序未确认 |
| 摄像头抓拍 | `main/camera_capture.{h,c}` | 桩 NOT_SUPPORTED | 型号/引脚 TBD |
| 启动序列 | `main/main.c` | 编译通过，未在设备链路验证 | NVS→Wi-Fi→载配对身份→外设 init→会话任务 |

## 构建依赖（2026-10-19）

- 工具链：ESP-IDF **v5.4.1**（`.local/esp-idf`，未入仓），target `esp32s3`。
- `main/idf_component.yml`：`esp_websocket_client`（WS 传输）、`led_strip`（状态灯）、
  `esp-sr`（AFE/AEC，条件启用）。
- 生成物 `firmware/esp32/sdkconfig`、`build/`、`managed_components/` 已加入 `.gitignore`。
- 构建脚本：`scripts/build_firmware.ps1`（清除 `MSYSTEM`、固定 ESP-IDF Python 3.12
  环境、加载 `export.ps1`、`idf.py set-target esp32s3 build`）。只编译，不烧录。
- **实测板卡（2026-10-20）**：ESP32-S3 rev v0.2，**16MB Flash + 8MB PSRAM**，
  MAC `1c:29:04:31:1c:58`；`sdkconfig.defaults` 已改为 16MB Flash。
- **2026-10-20 实机烧录/启动**：`effmeet2_robot.bin` = 954,880 B（含 esp-sr 与
  provisioning），app 分区 3MB 剩余 70%；CH340 COM3，`flash` 成功、Hash 校验通过，
  正常启动并进入 provisioning REPL。
- 编译期修正：`esp_websocket_register_events`（1.8.0 API）、`PRIx32` 格式符、
  16MB flash、补 `esp_websocket_client` 组件依赖。
- `dependencies.lock` 已生成（esp-sr 1.9.5 / esp_websocket_client 1.8.0 /
  led_strip 2.5.5 / esp-dsp 1.4.12）。
- **已烧录并启动**；外设仍为桩，未配对时进入串口配网 REPL。

## 已知开放集成点（bring-up 必做）

1. **命令下发通道**：已实现——`device_session_subscribe_commands` 订阅控制器事件 WS，
   过滤 `robot.command` 并按 `target_device_id` 分发；使用 `device_id` + `media_token`
   （会议绑定）。需要设备先通过 LAN 网关或公网到达控制器。
2. **Wi-Fi 配网**：已实现串口 REPL——未配对时进入 `provision` REPL，
   `provision <ssid> <pass> <controller_url> <meeting_id> <media_token>` 写 NVS 后重启；
   `provision_status` 不打印密钥。也可继续用 Kconfig 默认值。
3. **media_token 入 NVS**：operator 先 `POST /api/v1/meetings/{mid}/devices/{device_id}/pair`
   拿到 token，再provision 进设备 NVS（命名空间 `effmeet`，键 `meeting_id`/`media_token`）。
   token 有效期 1 小时（`bench.authenticate`），过期需重新配对。**密钥不入库、不打日志。**
4. **真 AEC**：`aec_afe` 需接 ESP-SR AFE 的回声参考通道 + 延迟对齐 + 双讲，替换软件互斥代理。
5. **引脚/电气核对**：`app_config.h` 的 I2S/摄像头 GPIO 为占位，须与最终板型和电气
   BOM 对齐（LED GPIO48、舵机 GPIO38 已实机可用）。I2S 链路本身（时钟/DMA/驱动）已验证，
   只差把 INMP441/MAX98357A 接到核对后的引脚。
6. **音频链路联调**：设备配网后跑 `scripts/run_bench.py` + `run_device_gateway.py`，
   验证上行 EFMA 流与 `speak` 播放到 `RobotReceipt(completed)` 全链路。

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
