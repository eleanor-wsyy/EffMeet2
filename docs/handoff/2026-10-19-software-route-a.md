# 2026-10-19 · 路线 A 远程音频链路（不依赖单片机与百炼 Key）

> 本轮只做不需要 ESP32 实机连接、也不需要 `QWEN_API_KEY` 的软件部分。
> 同日另见 [GitHub 新版用户端 APP 审查](2026-10-19-github-app-review.md)：新版是纯本地
> 演示版，不要直接覆盖功能版 `apps/web/`。
> 真实 LiveKit 本地房间已在后续补测跑通；公网/TLS/TURN/两端音频仍未验收。

## 本轮完成

### 0. GitHub 新版 APP 落地 — `apps/web-demo/` + `/app-demo/`

- 远端新版已复制到 `apps/web-demo/`，控制器挂载 `/app-demo/`；功能版 `/app/`
  与真实 API/LiveKit 完全不动。
- 新版自带 32 项测试通过；控制器新增 1 项 `/app-demo/` 静态路由与路径穿越保护测试。
- 详细审查见 [GitHub 新版用户端 APP 审查](2026-10-19-github-app-review.md)。

### 1. 用户端接入 LiveKit 远程音频 — `apps/web/`

- 新增 `media.js`：可注入 `Room`/`RoomEvent` 的媒体会话封装，负责
  connect → 按需发布麦克风 → 关闭 → 断开，并上报
  `connecting/connected/muted/live/reconnecting/closed/error` 状态。
- `app.js` 入会后向 `POST /api/v1/meetings/{meeting_id}/livekit-token` 申请短期 token，
  按需动态加载本地 SDK 并加入房间；会中麦克风按钮首次点击才发布麦克风轨，再点关闭；
  离开会议时断开。token 只存内存、只走 `Authorization` 头，不进 URL。
- LiveKit 未配置时，入会/候选/观点地图不受影响，底部显示
  “音频未配置：服务端未设置 LiveKit”，不伪造已连接。
- 前端 SDK 以 `vendor/livekit-client.esm.mjs`（2.23.0，Apache-2.0）入仓，不依赖 CDN；
  版本与来源见 `apps/web/vendor/README.md`。
- Service Worker 缓存版本升到 v2，并缓存 `media.js`；API/token/证据仍不缓存。
- 手机 QA 网关已放行 `POST /api/v1/meetings/{id}/livekit-token`、`/app/media.js` 与
  `/app/vendor/livekit-client.esm.mjs`；仍只允许该合成会议与 `remote_1` 身份。
- 主持人台架页 `/` 新增“加入远程音频”：operator-only host token（`canPublish=false`），
  订阅远程音轨并从本机扬声器播放，供现场拾取；不发布、不冒充参与者。
  页面会显示远程成员静音/取消静音、重连/恢复状态。
  对应 `POST /api/v1/meetings/{id}/livekit-host-token` 与 `services/controller/host-audio.js`。

### 2. 服务端解耦与安全边界 — `services/controller/app.py`

- token 端点不再同步等待 relay：参与者先拿到 token；relay 在后台尝试加入。
  返回新增 `relay_ready` / `relay_pending`。LiveKit 已配置但 ASR 未就绪时仍返回 `201`，
  不再让“远程成员连音频”被 relay 的 ASR 状态阻塞。
- CSP 的 `connect-src` 按 `LIVEKIT_URL` 的 `ws/wss` 源放行；未配置时仍只允许 `'self'`。
- 仍保留：只有 `remote_1/remote_2` 测试身份可申请 token；token 与 meeting/identity 绑定，
  只能发布麦克风源。

### 3. EFMA 固件编解码主机验证 — `scripts/test_efma_host.py`

- 用可选 `ziglang` 编译器在主机编译 `firmware/esp32/test/test_efma_host.c` 与
  `main/efma_codec.c`，不依赖 ESP-IDF、不连接单片机。
- 实际输出：`EFMA host tests passed (protocol.py parity)`；覆盖重复帧、错流、间隙隐藏、
  间隙过大、序列非法、短头。
- 边界：只证明纯 C 编解码与 `protocol.py` 一致；ESP-IDF 工程仍未编译/烧录。

### 4. 验收 harness 的 S1/S2 真实执行路径 — `tests/acceptance/real_chain.py`

- S1：接受真实 16 kHz mono WAV（`EFFMEET_ACC_MIC=<path>`）或用 `sounddevice`
  录默认麦克风（`=1`），校验 0.2–30 秒、非静音（≥ -50 dBFS）；失败记 `FAIL`。
- S2：把 PCM 通过真实 `/device/v1/audio` WebSocket 送入真实控制器，由真实 FunASR
  转写并落账；返回 `utterance.final` 才算通过。
- S3–S6 仍不伪造：百炼 Key、真实账号、机器人、现场麦未就绪时只报 `NOT_RUN`。

### 5. 部署 token 服务收口 — `deploy/livekit/token_service.py`

- 修复按 README 从仓库根运行时的 `ModuleNotFoundError: services`：脚本自行把仓库根加入
  `sys.path`，现在 `python deploy/livekit/token_service.py` 可直接启动。
- `MockIdentityProvider` 没有调用方认证，脚本现在**拒绝把它绑定到非回环地址**；
  要用 `--provider production` 并先接真实账号鉴权。
- 新增 6 项测试：mock 只发合成远程身份、缺字段 400、缺 LiveKit 配置 503、
  生产桩 501、healthz 配置状态、mock 公网绑定拒绝。

### 6. ESP32-S3 固件 ESP-IDF 编译 — `firmware/esp32/`

- 本机安装 **ESP-IDF v5.4.1**（`.local/esp-idf`，Git 忽略）与 esp32s3 工具链，
  `scripts/build_firmware.ps1` 固定 Python 3.12 环境并执行
  `idf.py set-target esp32s3 build`。
- 干净构建 **1204/1204**：`Project build complete`；`effmeet2_robot.bin` 约 **767KB**，
  app 分区 3MB 剩余 75%；bootloader 约 21KB。
- `idf.py size`：Flash Code 562,650 B + Flash Data 107,060 B；DIRAM 33.6%；
  **IRAM 16,383/16,384 B（99.99%）**，当前能链接但后续新增 IRAM 代码极易溢出。
- 编译期修正：`esp_websocket_register_events`（1.8.0 API）、`PRIx32` 格式符、
  8MB flash（2MB 放不下 3.1MB 分区表）、补 `esp_websocket_client` 组件依赖。
- **未烧录、未连接设备**；所有外设仍为 `ESP_ERR_NOT_SUPPORTED` 桩。

### 7. 远程音轨 → relay → 真实 ASR 端到端

- 新增 `scripts/smoke_livekit_remote_asr.py`：用 Python LiveKit SDK 以 `remote_1`
  发布 TTS WAV 音轨，等待 relay 订阅、真实 FunASR 转写并落账。
- 实测 **PASS**（meeting `41f48e73-d6d7-4d8a-b31b-0e7f25a7850f`）：
  - `relay_connected=true`，`active_tracks=1`，`last_error=null`
  - `channel=remote`，`speaker_id=remote_1`
  - 原文：`满意检测，用重量传感器比摄像头便宜很多。`
  - `stream_id=lk_5bfea5aa67934c82ad6f0d53dbb32379`，`start_ms=997`，`end_ms=5997`
- **修掉真实 bug**：`livekit_bridge.consume` 原先生成 `lk-<uuid>`，带连字符，
  违反 `UtteranceFinal.stream_id` 的 `^[a-z][a-z0-9_]{0,63}$`，真实音轨一直
  `REMOTE_ASR_FAILED`。改为 `lk_<uuid.hex>`，并在 `test_stream_segments_are_drained_and_closed`
  增加正则断言，防止回归。

### 8. S3 真实千问判断

- `tests/acceptance/real_chain.analyze` 走真实 bench worker + `qwen-plus`（DashScope），
  key 只从环境变量读取，不落盘、不打印。
- 实测 PASS（meeting `53e48b86-...`）：`status=uncertain`，`owner=remote_1`，
  5 条证据 ID 合法，`proposed_text` 为空、**没有生成候选**——符合“拿不准就弃权”。
- 首次重试遇到一次 `QWEN_NETWORK_ERROR`，重跑通过；这是网络瞬断，不是逻辑失败。
- 视觉 `qwen3-vl-plus` 未在本轮重跑（S3 的图片证据分支仍可单独验证）。

### 9. S6 真实现场回应跟踪

- `tests/acceptance/real_chain.response_tracking`：现场音频走真实 media WS + 真实
  FunASR，回应核对与观点地图走真实控制器。
- 实测 PASS（meeting `ebd15f64-...`）：现场转写
  `满意检测，用重量传感器比摄像头便宜很多。`，`asr_mode=real`，
  `verification_status=human_verified`，`viewpoint_response_status=responded`。
- **边界**：候选分析用本地 stub，本人确认用 `remote_1` 测试身份；这不是完整
  真人/真实账号验收，证据里已明确标注。

### 10. agy 审查修复

agy staffer 对提交前 diff 给出 8 项发现，已修复主要项：

- **CSP**：`connect-src` 同时放行 `ws(s)://` 与 `http(s)://`，否则 LiveKit JS SDK 的
  `/validate`/连通性 HTTP 探测会被浏览器拦截；同时校验 `netloc` 只允许
  `[A-Za-z0-9.:\[\]-]`，拒绝 `;` 等 CSP 注入字符（新增注入回归测试）。
- **媒体会话竞态**：`connectMedia` 保留局部 `session` 引用，快速离开/重入时只断开
  本次会话，不再误解散新会议；`media.js` 被取代的连接失败不再误报 `error`。
- **token 服务**：非 JSON/非对象请求体返回 400，不再 500（新增测试）。
- **lifespan**：关闭时取消并 `gather` 所有后台 relay 任务，再关闭 bridge。
- **验收错误信息**：S2 真实 ASR 失败保留底层异常文本。

仍未处理：`apps/web` 的 UI 级媒体集成测试（需要浏览器 DOM 环境），以及 agy 提到的
少量“缺少测试”项；功能修复已有单元/回归覆盖。

### 11. 设备 LAN 网关与事件 WS 设备 token

- 事件 WS（`/api/v1/meetings/{id}/events`）现在支持
  `{"device_id", "token", "after_seq"}`：`store.verify_device_token` 校验设备 token
  且必须绑定到当前会议；会话 token 仍兼容。
- `services/device_gateway.py` + `scripts/run_device_gateway.py`：控制器继续绑
  `127.0.0.1`；网关只放行 `GET /healthz`、`WS /device/v1/audio`、`WS /device/v1/playback`
  与 `WS /api/v1/meetings/{id}/events`，绑定 `0.0.0.0`，供局域网设备访问；
  HTTP/WS 双向中继，不暴露 operator 路由。

### 12. 固件命令下发与串口配网（2026-10-20）

- `device_session_subscribe_commands`：订阅控制器事件 WS，过滤 `robot.command`，
  按 `target_device_id` 分发；hello 用 `device_id` + `media_token`，会议绑定。
- `provision.c`：未配对时进入串口 REPL；`provision <ssid> <pass> <controller_url>
  <meeting_id> <media_token>` 写 NVS 后重启；`provision_status` 不打印密钥。
- 实机：ESP32-S3 N16R8（16MB Flash + 8MB PSRAM），COM3 烧录 954,880 B，
  Hash verified；启动日志正常；未配对时进入 REPL，`provision_status` 返回
  “nothing provisioned”。Wi-Fi 与控制器连通需要 Wi-Fi 凭据 + LAN 网关。

## 验证证据

- **联合验收（2026-10-19）**：同一个 real harness 同时设置 S1/S2/S3/S6 门槛，
  结果为 **S1 PASS、S2 PASS、S3 PASS、S6 PASS；S4/S5 NOT_RUN**
  （缺真实账号/机器人）。S3 真实千问返回 `uncertain` 且不生成候选；
  S6 现场 ASR + 回应核对 + 观点地图 `responded`。
- Python 全量：**129 tests OK（skipped=1）**（原 106 + 3 项 LiveKit 服务端测试 +
  6 项验收真实路径测试（S1/S2/S3/S6）+ 7 项部署 token 服务测试 +
  1 项 `/app-demo/` 静态路由测试 + 3 项设备事件 WS 测试 + 3 项设备网关测试）。
- 前端 Node：**41 tests pass**（原 32 + 新增 9 项媒体会话测试，含竞态回归）。
- EFMA 主机测试：`scripts/test_efma_host.py` → `EFMA host tests passed (protocol.py parity)`。
- S1 真实验收：用 `data/acceptance_speech.wav`（Windows TTS 合成语音，5.72s、
  -25.6 dBFS、16k mono s16le）跑出 `S1_capture PASS`；这是格式/时长/电平证据。
- S1 真实输入设备：`EFFMEET_ACC_MIC=1`、1 秒，默认输入设备（Senary Audio）实测
  -40.7 dBFS，harness `S1_capture PASS`；仍未验证 INMP441/浏览器采集，清单对应项
  不勾选“真人录音/机内麦”。
- S2 真实 FunASR：本地 `.venv-asr` 安装 `funasr==1.4.16` + SenseVoiceSmall（CPU），
  `run_local_asr.py` 在 `ws://127.0.0.1:10096` 就绪；同一 WAV 经真实媒体 WS 入账，
  转写 `满意检测，用重量传感器比摄像头便宜很多。`，`asr_mode=real`，
  `utterance_id=339d0572-...`，`S2_asr PASS`。ASR 把“满溢”听成“满意”并原样保留。
- S3 真实千问：`qwen-plus` 返回 `uncertain`，5 条证据合法、`owner=remote_1`、
  `proposed_text` 为空，**未生成候选**（符合弃权规则）；一次网络瞬断后重跑通过。
- S6 真实现场回应：真实 FunASR 转写 `满意检测，用重量传感器比摄像头便宜很多。`，
  `verification_status=human_verified`，`viewpoint_response_status=responded`；
  候选分析/本人确认使用 stub/测试身份，已在证据中标注。
- `node --check` 通过 `app.js` / `media.js` / `sw.js`。
- 浏览器实测（未配置 LiveKit）：以 `remote_1` 加入合成会议，页面显示
  “音频未配置：服务端未设置 LiveKit。”；入会、候选、观点地图无回归。
- 浏览器实测（配置 `LIVEKIT_URL=ws://127.0.0.1:7880` 但本机无服务器）：页面成功申请 token、
  动态加载 SDK、尝试加入房间，并显示“音频服务器连接失败。”；证明 token→SDK→连接
  路径真实执行，且失败不会阻塞会议功能。
- **真实 LiveKit 房间（2026-10-19 补测）**：本机启动 `livekit-server v1.13.10`（Windows
  release，无 Docker），`/app/` 参与端显示“音频已连接 · 点麦克风发言”，台架页 `/`
  显示“已加入远程音频”；LiveKit 日志出现 `remote_1` 与 `effmeet-host-*` 参与者。
  公网/TLS/TURN 与两端实际音频仍未验收。
- 台架页实测：新建会议后点“加入远程音频”，未配置 LiveKit 时显示
  “音频未配置：服务端需要 LIVEKIT_URL/API_KEY/SECRET。”，模块加载与错误路径正常。
- 回归冒烟：`scripts/smoke_bench.py` PASS（真实 HTTP+WS，合成 ASR/模型/TTS，
  `hardware_verified=false`）；`scripts/smoke_demo.py` PASS（12 项 mock 闭环）。
- `/app-demo/` 静态路由：控制器 `TestClient` 与浏览器均通过；功能版 `/app/` 未变。
- 静态资源：`/app/media.js` 与 `/app/vendor/livekit-client.esm.mjs` 均以
  `text/javascript` 返回；CSP 未配置 LiveKit 时为 `connect-src 'self'`。

## 未验证边界

- 本机已起 LiveKit 并验证本地房间、两端入房、`remote_1` 音轨→relay→真实 ASR 入账；
  **公网/TLS/TURN、浏览器实际麦克风发布与扬声器播放未验收**。
- relay 的远程 ASR 仍依赖本地 FunASR；未配置时 `relay_ready=false`，远程音轨不会入账。
- S1/S2 已用真实本地链路跑出 PASS：`.venv-asr` 的 SenseVoiceSmall 就绪后，
  `data/acceptance_speech.wav` → 真实 `/device/v1/audio` → 真实 FunASR 转写入账。
  输入是 TTS 合成语音，不是真人录音/INMP441；真人录音项仍未验收。
- 生产身份、公网部署、手机 4G/弱网仍属后续 bring-up。
- 已用 `QWEN_API_KEY` 跑 S3 真实 `qwen-plus`（key 只走环境变量，不入库/不打印）；
  S4/S5 仍需真实账号/机器人。未连接单片机，不构成任何硬件验收。

## 下一步

1. 浏览器/手机实测：实际麦克风发布、静音、离开、主持人扬声器播放；本地房间与
   `remote_1` 音轨→relay→ASR 已用 Python SDK 跑通。
2. 通过后补 `ProductionIdentityProvider` 与 TLS/TURN，再进入公网。
3. S1/S2/S3/S6 的软件链路已跑通；下一步补**真人录音**、INMP441/浏览器采集、
   S4 真实账号与 S5 机器人实播。
4. ESP-IDF 工程编译/烧录、真机回执、AEC 与机器人实播仍属路线 B/决赛 bring-up。

## 本机环境与复现（2026-10-19）

- PyPI 直连/清华/中科大在本机受证书吊销检查与代理节点影响；可用
  `-i https://mirrors.aliyun.com/pypi/simple/`。
- GitHub 网页/API 可用；Release 资产走 `https://gh-proxy.com/https://github.com/...`
  镜像下载。
- LiveKit 本地服务器：`.local/tools/livekit-server.exe`（v1.13.10 Windows release，
  已被 Git 忽略）。启动命令见 `deploy/livekit/README.md`。
- mihomo 主选择组原节点 `SG - 新加坡 01` 不可用；切到 `HK - 香港综合` 或
  `US - 圣何塞 - 04` 后 PyPI/GitHub/Google 端点恢复。
- `sounddevice 0.5.6` 已装入主 `.venv`；本机默认输入设备可用（S1 1 秒实测
  -40.7 dBFS）。
- `.venv-asr`（Python 3.12）已装 `funasr==1.4.16`/`torch==2.5.1`；SenseVoiceSmall
  权重在 `data/models`（约 897MB）。复现：
  `.\.venv-asr\Scripts\python.exe scripts/run_local_asr.py`，另开终端设
  `FUNASR_WS_URL=ws://127.0.0.1:10096`。

## 本轮未做（需要外部资源或不在初赛关键路径）

- LiveKit 公网/TLS/TURN：本机已实跑本地房间、两端入房、`remote_1` 音轨→relay→真实 ASR
  入账；公网/TURN、浏览器实际麦克风发布与扬声器播放仍未完成。
- 真人录音/INMP441/浏览器采集：S1 已用本机默认输入设备跑通，但输入是 TTS/默认设备，
  不是真人录音或最终机内麦；清单对应项仍未勾选。
- ESP-IDF 烧录/实机：工程已编译通过（v5.4.1），但**未烧录、未连接设备**；
  外设驱动仍是桩，硬件链路未验收。
- 生产身份、公网 TLS/TURN、手机 4G/弱网：需要账号体系与网络环境。
- agy staffer 独立审查：网络修复后仍返回
  `FAILED_PRECONDITION (400): User location is not supported for the API use.`
  （账号地区限制，换美国节点也一样），未取得外部审查结果。
