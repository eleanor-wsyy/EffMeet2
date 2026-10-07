# 用户端APP（10.7）

2026-10-07 用户端交付快照。对应 Figma 手机参与者界面，不是仓库根目录的主持人/调试工作台。

## 交付内容

- 三个界面：入会页、会中页、观点地图页。
- 最新视觉精修：保留白色 → `#FFEFBA` 背景渐变及既有文案、交互。
- 底部候选弹层；在「查看状态」中点击「请机器人提醒」。
- 默认 4 条独立待确认演示数据，逐条确认、不重复提醒。
- 前端、同源控制器后端、接口契约、资源、启动脚本及测试全部包含。

本目录是独立可运行快照，基于 `aa7cdab76ae7401031735ab07a6f3da782c2b942` 加入已验证的用户端实现。保留原始支撑代码/资料以便联调；本次提交仅新增本目录，未替换仓库根目录的工作台或后端。主要用户端代码在 `apps/web/`。

## 启动（Windows / PowerShell）

先在克隆后的 EffMeet2 仓库根目录打开终端，然后进入本目录。以下命令必须在本目录执行，不是在外层仓库根目录执行。

```powershell
Set-Location -LiteralPath "用户端APP（10.7）"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-media.txt
.\.venv\Scripts\python.exe scripts/run_participant.py --port 8765 --db .local/participant.sqlite3
```

打开 `http://127.0.0.1:8765/app/`。前端无需 npm 安装或打包；不要直接双击 HTML，否则无法接入同源后端。

默认端口如果已被占用，可将两个脚本的 `--port` 一并改为其他空闲端口。现有预览使用 8876，不受上述独立实例影响。

## 创建多条待确认演示

另开终端并进入同一目录，执行：

```powershell
.\.venv\Scripts\python.exe scripts/seed_participant_demo.py --port 8765 --candidates 4
```

脚本输出邀请链接和会议 ID；使用该链接入会，填写昵称，逐条打开「查看状态」并点击「请机器人提醒」。所有数据均为明确标记的人工合成证据，不是真实会议录音或模型判断。候选有效期为 120 秒；过期后主动请求提醒会由后端重新校验，并非重新打开弹层就自动延期。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --test apps/web/tests/state.test.js
```

交付前验证：85 项 Python 测试、29 项 Node 测试通过。

## 目录索引

| 位置 | 用途 |
| --- | --- |
| `apps/web/` | 手机前端源码、样式、SVG 资源、状态测试和详细接入说明 |
| `services/controller/` | 已接入用户端的同源后端快照 |
| `services/relay/` | 现有音频 / LiveKit 中继支撑代码 |
| `scripts/run_participant.py` | 本地用户端启动入口 |
| `scripts/seed_participant_demo.py` | 1～4 条独立候选的模拟会议创建脚本 |
| `contracts/`、`fixtures/` | 接口契约、模拟输入 |
| `tests/` | 后端与用户端集成测试 |
| `docs/`、`assets/` | 产品资料和原始设计资源 |

## 范围与限制

- 这是已完成的本地联调用户端，不是正式公网生产部署。
- 本机演示身份不是正式账号登录；服务仅监听 `127.0.0.1`。
- 默认使用 mock 模型/机器人回执，不代表机器人真的播报。
- 麦克风仅完成真实权限检查；用户端尚未接通 LiveKit 音频发送，不能称为已持续录音。
- 现场 AI 描述、会议结束事件及完整离线 PWA 尚未接通。
- 未提交数据库、会话令牌、真实 API 密钥、虚拟环境或依赖缓存。

更详细的接口、交互和验收记录见 `apps/web/README.md`。
