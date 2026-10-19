# LiveKit 公网部署骨架（NOT-VERIFIED）

> 2026-10-16 搭出。目标：把仓库里**已实现且经测试**的 LiveKit 接入
> （`services/relay/livekit_bridge.py` 订阅房间音轨跑离线 ASR、
> `services/relay/livekit_token.py` 服务端签发 token）从"仅回环本机 + 合成测试身份"
> 推进到"公网可达 + 生产鉴权"。**本骨架未部署、未联调、未上公网。**

## 现状 vs 终局

| 维度 | 现状（已实现） | 终局（本骨架要补的） |
|---|---|---|
| token 签发 | `issue_token()` 服务端持密钥，前端只拿一次性 token | 同左，但经公网 token 服务暴露 |
| 身份鉴权 | 仅合成 `remote_1/remote_2`（`app.py: livekit_token` 门控） | 真实账号鉴权（`ProductionIdentityProvider`，**桩，未实现**） |
| 网络 | relay 只接受回环本机、无 Origin、无查询参数 | 公网 LiveKit 房间 + TLS + TURN |
| relay 订阅 | `LiveKitBridge.join/consume` 已实现，按会议一房间 | 同左，部署到可达 LiveKit 服务器的环境 |

## 组件

- `token_service.py` — FastAPI，复用 `issue_token`，前置 `IdentityProvider` 鉴权缝；
  可从任意目录以 `python deploy/livekit/token_service.py` 启动。
  - `MockIdentityProvider`：复刻台架行为（仅合成远程身份），**非生产鉴权**；
    没有调用方认证，因此脚本拒绝把它绑定到非回环地址。
  - `ProductionIdentityProvider`：**NOT-VERIFIED 桩**，未接真实账号系统前会抛 501。
- `gateway.env.example` — 环境变量模板（无密钥）。复制为 `.env` 填密钥，**不提交**。
- `livekit.yaml` — livekit-server 配置模板（密钥走环境变量，不内联）。
- `docker-compose.yml` — livekit-server + redis + TURN 自托管栈骨架。

## 已接上的客户端与接口

- 用户端 `apps/web/` 已接最小 LiveKit 客户端：入会后向
  `POST /api/v1/meetings/{meeting_id}/livekit-token` 申请短期 token，加入房间；
  会中麦克风按钮按需发布/关闭麦克风轨，离开会议时断开。
- 主持人台架页 `/` 新增“加入远程音频”：向
  `POST /api/v1/meetings/{meeting_id}/livekit-host-token` 申请
  `canPublish=false` 的 host token，订阅远程音轨并从本机扬声器播放，供现场拾取。
  只订阅、不发布；无 LiveKit 配置时明确显示“音频未配置”。
- 本机实测 `scripts/smoke_livekit_remote_asr.py`：`remote_1` 发布 TTS 音轨，
  relay 订阅并由真实 SenseVoiceSmall 转写入账（`channel=remote`，`last_error=null`）。
  同时修复了 relay `stream_id` 带连字符违反契约的 bug。
- token 端点现在把“远程成员入会”和“relay 订阅转写”解耦：LiveKit 已配置但
  ASR 未就绪时仍返回 `201`，并带 `relay_ready=false`/`relay_pending=true`；
  relay 在后台尝试加入。参与者音频不再被 relay 的 ASR 状态阻塞。
- CSP 会按 `LIVEKIT_URL` 的 `ws/wss` 源放行 `connect-src`；未配置时仍只允许同源。
- 前端 SDK 为本地 vendored `apps/web/vendor/livekit-client.esm.mjs`（2.23.0，Apache-2.0），
  不需要外部 CDN。

### 本机无 Docker 时的 Windows 实跑（已验证可连接）

```powershell
# 下载到被 Git 忽略的 .local/tools（也可用任意 GitHub 镜像）
curl -L -o .local/tools/livekit.zip https://github.com/livekit/livekit/releases/download/v1.13.10/livekit_1.13.10_windows_amd64.zip
cd .local/tools; unzip livekit.zip; cd ../..
$env:LIVEKIT_KEYS="devkey: secret"
.\.local\tools\livekit-server.exe --dev --bind 127.0.0.1 --node-ip 127.0.0.1

# 另开终端，控制器/台架使用同一组配置
$env:LIVEKIT_URL="ws://127.0.0.1:7880"
$env:LIVEKIT_API_KEY="devkey"
$env:LIVEKIT_API_SECRET="secret"
.\.venv\Scripts\python.exe scripts/run_bench.py --port 8768
```

- 用户端 `/app/` 已实际连上该本地房间，显示“音频已连接 · 点麦克风发言”。
- 台架页 `/` 的“加入远程音频”已实际连上，显示“已加入远程音频”。
- 同一台机器上两个页面需使用**同一个控制器端口/数据库**（例如都用 8768），
  否则会议 ID 不在同一账本。
- 浏览器首次发布麦克风会弹系统权限提示，必须由使用者本人允许；自动化测试
  不能代替这一步。
- `--dev` 与 `devkey/secret` 只用于本机验证，不能用于公网；公网仍须 TLS/TURN、
  生产身份与真实密钥。

以上仅代表客户端代码与接口接通；**本环境已起 Windows 本地服务器并验证两端入房，
但真实公网/TLS/TURN 和两端实际音频仍未验收。**

## 部署步骤（bring-up，全部 NOT-VERIFIED）

1. 准备域名 + TLS（LiveKit 需 wss/https；媒体走 UDP/TCP 端口段或 TURN）。
2. `cp gateway.env.example .env`，填 `LIVEKIT_URL/API_KEY/API_SECRET` 等密钥。
   注意 `livekit.yaml` **不会**展开 `${...}`：compose 用
   `LIVEKIT_KEYS="<key>: <secret>"` 注入密钥，不要把密钥写进挂载的 YAML。
3. `docker compose up -d livekit redis turn` 起自托管栈（或用 LiveKit Cloud）。
   `room.auto_create` 必须为 `true`：控制器不通过 server API 预建房间，
   参与者和 relay 按 `meeting_id` 直接加入。
4. 实现 `ProductionIdentityProvider.authorize()`：校验调用者会话、确认其为该
   `meeting_id` 参与者、返回规范 identity、拒绝跨会议/冒名。
5. 起 token 服务：`python deploy/livekit/token_service.py --provider production`
   （默认绑回环；公网暴露须置于 TLS 反向代理后）。
6. 起 relay（需 ASR）：见 `services/relay/README.md`，`scripts/run_bench.py`。
   relay 用 `LIVEKIT_*` 以 relay 身份订阅房间（`canPublish=false`）。
7. 远程成员经 token 服务拿 token → 入会发布麦克风轨 → relay 订阅 → 离线 ASR → 入控制器账本。

## 安全边界（不可妥协）

- 密钥仅存服务端环境变量；不进前端、固件、镜像、日志、URL。
- token 短时效、与 identity 绑定；relay token `canPublish=false`。
- 公网暴露前必须用 `ProductionIdentityProvider` 替换 mock 门控；mock 仅供合成测试。
- 不把回环台架入口（`127.0.0.1:8768` 等）当公网共享入口。

## 验证边界

本环境未起任何容器、未连任何 LiveKit 服务器、未签发真实 token。
"完成"仅指配置/服务骨架与既有 `issue_token`/`LiveKitBridge` 对齐，**不代表公网链路已验收**。
