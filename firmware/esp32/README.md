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

**2026-10-20：已用 ESP-IDF v5.4.1 编译并烧录到实机（ESP32-S3 N16R8，16MB Flash + 8MB PSRAM），启动通过；未配对时进入串口配网 REPL；状态灯/舵机已实现，其余外设仍为桩。**
**2026-10-19：ESP-IDF v5.4.1 编译通过（`Project build complete`）。**
**2026-10-16：已搭出 ESP-IDF 工程骨架（当时未编译）。**
模块状态表、开放集成点与契约对齐参照见 [docs/FIRMWARE_STATUS.md](docs/FIRMWARE_STATUS.md)。

- 工程树：`CMakeLists.txt` / `sdkconfig.defaults` / `partitions.csv` / `main/`（组件）。
- 已按仓库现有契约落地：EFMA 帧编解码（`main/efma_codec.c`，`protocol.py` 的 C 移植，纯 C 可主机测）、
  WebSocket 传输（`main/ws_transport.c`）、设备会话/命令/回执状态机（`main/device_session.c`）。
- 未配对时进入串口配网 REPL：`provision <ssid> <pass> <controller_url> <meeting_id> <media_token>`
  写入 NVS 后重启；配对后订阅控制器事件 WS，按 `target_device_id` 分发 `robot.command`。
- 已实现外设：状态灯（WS2812，GPIO48）、舵机（MG90S，GPIO38 LEDC）、I2S 拾音（INMP441）与 I2S 播放（MAX98357A，I2S 引脚仍为占位，REPL `mic`/`tone` 可实测）。仍桩：AFE/AEC、摄像头。
- **EFMA 编解码已主机编译并通过测试（2026-10-19）**：`scripts/test_efma_host.py` 用可选的
  `ziglang` 编译器构建 `test/test_efma_host.c`，输出 `EFMA host tests passed (protocol.py parity)`。
- **ESP-IDF 工程已编译并烧录启动**：`effmeet2_robot.bin` 约 955KB（含 esp-sr 与配网），app 分区 3MB 剩余约 69%；
  工具链在 `.local/esp-idf`（Git 忽略），构建脚本见下。**已烧录并启动，未配对。**
  主机测试只证明材料帧编解码与 `protocol.py` 一致，不代表设备链路。

当前 Demo 阶段音频走电脑伴侣应用（路线A），固件为最终形态（路线B）的核心。

## 本机构建（不需要连接单片机）

```powershell
# 首次：把 ESP-IDF v5.4.1 放到 .local/esp-idf，并安装 esp32s3 工具链
# 然后：
powershell -ExecutionPolicy Bypass -File scripts/build_firmware.ps1
```

该脚本清除 Git Bash 的 `MSYSTEM`、设置 `IDF_PATH`、加载 `export.ps1`，
再执行 `idf.py set-target esp32s3 build`。只编译，不烧录。

## 关键约束

- 不承担 FunASR 或通用大模型推理
- 网络发送完成 ≠ 播报完成，需机内播放回执
- 舵机运动不引发复位
