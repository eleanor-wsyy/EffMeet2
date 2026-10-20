# 2026-10-20 · 换电脑续作指南（烧录/联调现状交接）

> 目标机器换机用。当前固件已烧录实机并完成全链路验收；本单告诉你在新电脑上
> 如何恢复环境、继续联调。不包含任何密钥；密钥只走环境变量/设备 NVS。

## 一、实机烧录现状（截至 2026-10-20 晚）

- 板卡：ESP32-S3 rev v0.2，N16R8（16MB Flash + 8MB Octal PSRAM），
  MAC `1c:29:04:31:1c:58`。USB-UART（CH340）在 COM3（**换电脑后口会变**，
  `scripts/flash_firmware.ps1` 不带参数会自动探测）。
- 固件分支：`feat/software-route-a-20261019`，最新固件相关提交 `df55750`
  （含 I2S 音频、cmdq 命令分发、TCP_NODELAY、PCM 统计、REPL 诊断命令）。
- **实机已验证**：状态灯（GPIO48）、舵机初始化（GPIO38）、I2S 收/播 DMA 与时钟
  （`i2srate` 50/s）、Wi-Fi 入网、事件 WS 长连、robot.command 下发、
  上行 EFMA 流（bind+`uplink`）、speak 全链路（TTS→EFMA 下行→逐帧 ack→
  播放排空→`RobotReceipt completed`；解码 PCM peak=30173 rms=2441 为真实语音）。
- **未验证（等硬件）**：INMP441/MAX98357A 实际接线（`app_config.h` 引脚是占位：
  麦 4/5/6，功放 15/16/17/18，EN=18）、真声音、摄像头（型号 TBD）、真 AEC。
- 启动形态：未配对/配对后都进 `effmeet>` REPL（配对后同时跑会话）。

## 二、新电脑环境重建

1. **仓库**：clone 后切 `feat/software-route-a-20261019`。
2. **Python**：`.venv` + `pip install -r requirements.txt`（含 `pyserial`，
   `reprovision_board.py`/串口脚本要用；PyPI 受阻时用
   `-i https://mirrors.aliyun.com/pypi/simple/`）。
3. **ESP-IDF v5.4.1**：放到 `.local/esp-idf`（Git 忽略，需重新装），
   并安装 esp32s3 工具链 + Python 3.12 venv
   （`~/.espressif/python_env/idf5.4_py3.12_env`）。
   构建脚本 `scripts/build_firmware.ps1` 已处理 MSYSTEM/venv 锁定。
   首次构建约 2 分钟（增量更快）。烧录 `scripts/flash_firmware.ps1`。
4. **ASR（可选）**：`.venv-asr`（Python 3.12）装 funasr/torch，权重在 `data/models`
   （约 897MB，不入仓）；起 `scripts/run_local_asr.py`。
5. **LiveKit（可选）**：`.local/tools/livekit-server.exe`（不入仓，
   Release 资产走 `gh-proxy.com` 镜像下载）。

## 三、联调拓扑（换电脑后按此恢复）

- **板子联网**：校园网 GAFA_Stu 有客户端隔离（板与 PC 不同网段互不可达），
  用 **PC 移动热点**：SSID `EffMeet-Link` / 密码 `effmeet88`，
  PC 侧 IP 固定为 192.168.137.1。WinRT 可编程开关（PowerShell）：

  ```powershell
  $profile = [Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime]::GetInternetConnectionProfile()
  $mgr = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]::CreateFromConnectionProfile($profile)
  $cfg = New-Object Windows.Networking.NetworkOperators.NetworkOperatorTetheringAccessPointConfiguration
  $cfg.Ssid='EffMeet-Link'; $cfg.Passphrase='effmeet88'
  $cfg.Band=[Windows.Networking.NetworkOperators.TetheringWiFiBand]::TwoPointFourGigahertz  # ESP32-S3 无 5GHz
  $mgr.ConfigureAccessPointAsync($cfg); $mgr.StartTetheringAsync()
  ```

  注意：热点默认 5GHz 时 ESP32-S3 扫不到；Windows 空闲会自动关热点，需重开。
- **服务端**（两个进程都建议不带 `| head` 以保留日志）：

  ```powershell
  # 终端1：bench 控制器（本地回环）
  $env:EFFMEET_TTS="windows"; $env:EFFMEET_ROBOT_ID="robot_a"
  $env:QWEN_API_KEY="<用户环境变量，不入仓>"
  .\.venv\Scripts\python.exe scripts\run_bench.py          # 127.0.0.1:8768
  # 终端2：设备网关（暴露给板子）
  .\.venv\Scripts\python.exe scripts\run_device_gateway.py  # 0.0.0.0:8799
  ```

- **板子配网/配对**：`scripts/reprovision_board.py --meeting <meeting_id>`
  （pair + 串口写 NVS + 自动重启）。media_token **1 小时过期**，过期后
  playback 报 `INVALID_MEDIA_TOKEN`，重跑该脚本即可。
- **验收注入**：候选用 `store.analyze(mid, {"evidence_ids":[...]}, "possibly_unresponded")`
  直接落（Qwen 真实调用按设计宁缺毋滥，三次 uncertain 不出候选——模型路径已验证，
  判定策略属产品行为）；robot.command 也可直接向 bench DB `emit` 做注入测试。

## 四、REPL 诊断命令（实机）

`provision` / `provision_status` / `led <idle|notice|error|off>` /
`mic`（1s RMS/peak+ISR 计数）/ `tone [freq] [ms]`（正弦试音）/
`i2srate`（DMA 完成率，应 ≈50/s）/ `uplink <session_id> <stream_id> <stream_key>`
（须先 `POST /api/bench/meetings/{mid}/media-bindings` 绑定同配置会话）。

## 五、踩坑备忘（详见 2026-10-20-esp32-bringup.md）

1. `i2s_channel_read/write`、`esp_websocket_client_send_*` 超时参数是**毫秒**，
   误传 `pdMS_TO_TICKS()` 会缩小 100 倍（FreeRTOS_HZ=100）。
2. `i2s_channel_register_event_callback` 必须在 enable 之前调用。
3. `esp_websocket_client_start` 是异步的，start 后要等握手完成再判 is_connected。
4. 板端 TCP 默认开 Nagle，小 ack 被扣 ~175ms；`ws_transport.c` 用 ext transport
   （`esp_transport_tcp`+`esp_transport_ws`，注意 ws_path/headers 要自己配）
   设 `TCP_NODELAY` 修复到 24ms/帧。
5. bench 命令默认目标 `host_speaker_test`（测试钉死），真机须 `EFFMEET_ROBOT_ID`。
6. IRAM 接近满（esp-sr 占大头），新增固件代码默认进 Flash。

## 六、回归验证

- Python：`.\.venv\Scripts\python.exe -m unittest discover -s tests -q`
  （当前 129 通过，1 skip）。
- 固件：`scripts/build_firmware.ps1` → `scripts/flash_firmware.ps1` →
  串口 REPL `i2srate` / `mic` / `tone`。
- 全链路：reprovision → decide confirm → 串口看 `playback done: frames=…`
  与回执 completed。
