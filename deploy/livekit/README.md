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

- `token_service.py` — FastAPI，复用 `issue_token`，前置 `IdentityProvider` 鉴权缝。
  - `MockIdentityProvider`：复刻台架行为（仅合成远程身份），**非生产鉴权**。
  - `ProductionIdentityProvider`：**NOT-VERIFIED 桩**，未接真实账号系统前会抛 501。
- `gateway.env.example` — 环境变量模板（无密钥）。复制为 `.env` 填密钥，**不提交**。
- `livekit.yaml` — livekit-server 配置模板（密钥走环境变量，不内联）。
- `docker-compose.yml` — livekit-server + redis + TURN 自托管栈骨架。

## 部署步骤（bring-up，全部 NOT-VERIFIED）

1. 准备域名 + TLS（LiveKit 需 wss/https；媒体走 UDP/TCP 端口段或 TURN）。
2. `cp gateway.env.example .env`，填 `LIVEKIT_URL/API_KEY/API_SECRET` 等密钥。
3. `docker compose up -d livekit redis turn` 起自托管栈（或用 LiveKit Cloud）。
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
