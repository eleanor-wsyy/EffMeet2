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
  （正弦试音）、`i2srate`（测 1s 内 DMA 完成率）、`uplink <session_id> <stream_id>
  <stream_key>`（触发上行 EFMA 流，须先 bench 绑定会话）。ISR/溢出计数器保留在
  `audio_capture`/`audio_playback` 里作 bench 诊断。
- **speak 全链路验收（2026-10-20 傍晚）**：决定 → robot.command → 板子接收 →
  Windows TTS → EFMA 下行 → 逐帧 ack → 播放排空 → **RobotReceipt completed**
  （回执 accepted/started/completed 完整入账）。TCP_NODELAY 修复后帧间隔从
  ~175ms 降到 **22-28ms**（实时期 20ms），700+ 帧稳定传输。
  注意：media_token 有 **1 小时 TTL**（`bench.authenticate`），过期表现为
  playback 报 `INVALID_MEDIA_TOKEN`（events WS 仍能连），需重新 pair + provision。
- **Wi-Fi + 命令链路边端验证（2026-10-20 下午）**：校园网 GAFA_Stu 有客户端隔离
  （板 10.15.120.x / PC 10.15.155.x 互不可达），改用 **PC 移动热点**（WinRT
  `NetworkOperatorTetheringManager` 可编程开关；热点默认 5GHz 须强制 2.4GHz，
  ESP32-S3 不支持 5GHz）。热点 `EffMeet-Link`/`effmeet88`，PC 为网关
  192.168.137.1，板得 192.168.137.167。bench(8768)+device_gateway(8799) 起在本机，
  板配对后事件 WS 长连成功；注入 `robot.command`（light/speak/stop）后板子
  随即发起 `/device/v1/playback` 连接——**命令下发链路全通**。
- 固件修复：`command_task` 原先把异步 `ws_transport_start` 当同步用，
  start 后立即判 `is_connected` 导致反复销毁重连（2.3s 循环），已加 5s 握手等待；
  `wifi_init_sta` 现在等 DHCP 拿到 IP 再开 socket；REPL 改为配对后也常驻，
  重新配网不再需要擦 NVS（0x9000 区）。

## 终局目标（路线B）

机器人脱离电脑、经 Wi-Fi 直连云端，独立完成：机内麦拾音 → AFE/AEC 前处理 →
Wi-Fi 推 PCM（EFMA 帧）→ 收 `speak` 命令实播并回**播放完成回执**（网络发完≠播完）→
单轴转头 + 状态灯 + 摄像头 JPEG 抓拍。声学上能**边播边听**不误触发（真 AEC）。

## 模块状态表

| 模块 | 文件 | 状态 | 说明 |
|---|---|---|---|
| EFMA 帧编解码 | `main/efma_codec.{h,c}` | **主机测试通过（2026-10-19）**，未在设备链路验证 | `protocol.py` 的逐字段 C 移植；纯 C 无 ESP 依赖。`scripts/test_efma_host.py` 用 ziglang 编译并运行 `test/test_efma_host.c`，全部断言通过 |
| WebSocket 传输 | `main/ws_transport.{h,c}` | 编译通过，未在设备链路验证 | `esp_websocket_client` 封装；Bearer 头鉴权（不走 URL/Origin，对齐 `media.py`） |
| 设备会话/协议状态机 | `main/device_session.{h,c}` | **实机链路验证（2026-10-20）**：事件 WS 长连 + robot.command 下发触发播放流 | 配对/Hello、上行流、播放握手、回执状态机、命令分发 |
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

- ESP-IDF v5.4.1 工程已编译并烧录实机（COM3），启动通过，Wi-Fi/事件 WS/命令
  下发已实机验证（经 PC 热点 + LAN 网关，2026-10-20）。
- I2S 音频驱动 DMA/时钟实机验证通过；**真实声音未验证**（INMP441/MAX98357A
  尚未接到占位引脚）。
- EFMA 编解码已用可选 `ziglang` 编译器主机编译并通过：`scripts/test_efma_host.py` 输出
  `EFMA host tests passed (protocol.py parity)`，覆盖重复帧/错流/间隙隐藏/间隙过大/序列非法/短头。
  这是**主机逻辑验证**，不是设备链路验证。
- 上行 EFMA 音频流（设备→网关→控制器解码/入账/会话生命周期）已实机验证
  （2026-10-20，REPL `uplink` 触发 + bench 绑定）；因麦克风未接线，内容为零声。
  ASR 未启动故无转写（可选：起 `scripts/run_local_asr.py` 后重测）。
- speak 播放链路已实机验收：Windows TTS → EFMA 下行 → 板子实播（功放未接线，
  无声）→ 播放排空 → `RobotReceipt(completed)`。真声音待 MAX98357A 接线后复测。
- AFE/AEC 与摄像头仍为桩，未验收。
