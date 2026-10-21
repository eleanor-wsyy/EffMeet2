# 在议 · effmeetbot

**在线，不等于在场。**

![在议整机渲染](hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/renders/01_hero.png)

在议是一台守在会议桌边的 AI 桌面伙伴，帮线上参会的人重新“坐回桌边”：现场材料随手一拍直达远程成员手机；它安静旁听全程，发现你的观点被淹没时先悄悄问你一句，**你点头它才转向现场发声**；散会后观点地图一目了然，每条记录都能回到当时的原话。

天猫 AI 黑客松 · 高校挑战赛「效率进化」赛道参赛作品。

- **路线 A（当前参赛 Demo）**：电脑伴侣应用承载本地 AI（FunASR 转写 + 千问候选判断 + SQLite 事件账本）
- **路线 B（最终形态）**：去除电脑依赖，机器人经 Wi-Fi 直连云端，手机/平板即可完整使用

## 三个入口

| 入口 | 内容 | 位置 |
|---|---|---|
| 产品官网 | 品牌、交互叙事、工业设计、技术链路与完成度 | `site/` |
| 交互 Demo | 纯静态用户端，走通“候选 → 本人确认 → 模拟播报 → 观点地图” | `site/demo/`（源：`apps/web-demo/`） |
| AI 判断实验台 | Gradio + 真实 `qwen-plus`，三态判断与证据校验 | `apps/ai-demo/` |

## 现在就能跑

无需机器人、麦克风或模型账号。Python 3.11+（Windows / Python 3.13 实测）：

```powershell
git clone https://github.com/eleanor-wsyy/EffMeet2.git
cd EffMeet2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/run_demo.py
```

浏览器打开 `http://127.0.0.1:8765`：新建会议、加入发言、以“线上成员”身份请求机器人提醒，可完整走通闭环（全部 `mode=mock`，FakeAnalyzer 替代模型，FakeRobot 只记录命令不发声）。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests   # 129 项单元测试
.\.venv\Scripts\python.exe scripts/smoke_demo.py           # 真实 HTTP 冒烟（需先保持服务运行）
```

纯静态界面版 `apps/web-demo/` 不接任何后端，数据只在本机 `localStorage`：

```powershell
.\.venv\Scripts\python.exe -m http.server 8000
# 打开 http://127.0.0.1:8000/apps/web-demo/
```

官网本地预览：`python -m http.server 8000 --directory site`，打开 `http://127.0.0.1:8000/`。

AI 判断实验台需要服务端环境变量 `QWEN_API_KEY`；未配置时界面明确报错，不返回伪造结果：

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/ai-demo/requirements.txt
$env:QWEN_API_KEY = "sk-..."
.\.venv\Scripts\python.exe apps/ai-demo/app.py
```

注意：带真实 Key 的服务只在本机或受控创空间运行，不要把本地控制器或模拟鉴权直接暴露到公网。默认数据库 `data/demo.sqlite3` 已被 Git 忽略，可用 `EFFMEET_DB_PATH` 指定别的路径。

## 系统全景

| 模块 | 职责 | 状态 |
|---|---|---|
| `services/controller/` | FastAPI + SQLite 账本：会议、候选/确认门控、幂等执行、原文记录、共享原图、观点地图 | ✅ 129 项测试通过（2026-10-21） |
| `services/relay/` | EFMA 帧、FunASR 接入、TTS、受控媒体 WebSocket | ✅ 真实链路补测 PASS（10-19） |
| `apps/web/` | 用户端功能版 `/app/`：入会、LiveKit 远程音频、确认、观点地图 | ⚠️ 真实服务器两端音频未验收 |
| `apps/web-demo/` | 用户端纯本地演示版：完整 UI，不接后端 | ✅ 可独立部署 |
| `apps/ai-demo/` | Gradio 判断实验台：真实千问、三态、证据 ID 校验、弃权 | ✅ 自检 7 组全过；真实调用待 Key |
| `firmware/esp32/` | ESP32-S3 固件：EFMA 编解码、UART 配网、WS2812、舵机/I2S 驱动 | ⚠️ 已编译烧录启动；外设实机联调进行中 |
| `deploy/livekit/` | 公网 LiveKit 部署骨架（token 服务、自托管栈） | ⚠️ NOT-VERIFIED |
| `contracts/v1/` | 前后端共用数据契约（有一致性测试） | ✅ |
| `hardware/` | 机器人结构：32 件参数化模型、BOM、打印与装配文档 | ⚠️ 装配进行中 |

千问经阿里云百炼 DashScope API 调用（判断 `qwen-plus`，视觉 `qwen3-vl-plus`），API Key 仅存服务端，不进前端或固件。

## 当前状态与边界

**已验收**：本地模拟闭环全链路；真实录音转写 → 千问判断 → 本人确认 → 命令排队的软件联调；LiveKit 本机两端入房与真实 ASR 入账（10-19 补测）；ESP-IDF v5.4.1 固件编译烧录启动；32 个结构件参数化交付（逐件哈希校验）；舵机与 ILI9341 屏分段点亮。

**未验收（不宣称）**：机器人实机连续会议播报与转头动作；AEC 边播边听；LiveKit 公网部署与两端实机音频；真人录音与整机连续会议。硬件未完成制造放行。官网中的机器人图为 v6 工程渲染，不是实机照片；播报动作为目标效果，当前以模拟回执演示。

## 仓库地图

- **官网与提交物料**：[site](site/)（静态站，可直接部署到魔搭创空间）、[参赛提交文案](docs/product/参赛提交文案_2026-10-21.md)
- **硬件总入口**：[hardware/robot-design](hardware/robot-design/README.md)（[BOM 采购](hardware/robot-design/round-yaw-v2/BOM.md) → [v6 打印候选](hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/README.md)）
- **装配执行**：[2026-10-21 装配实施方案](docs/handoff/2026-10-21-装配实施方案.md)；历次打印作业包在 [hardware/print-jobs](hardware/print-jobs/README.md)
- **软件交接**：[docs/handoff](docs/handoff/README.md)（10-19 路线 A 链路、10-20 ESP32 bring-up）
- **技术资料**：[论文依据与技术路径](docs/product/EffMeet2_论文依据与技术路径.html)、[v1 接口契约](docs/product/EffMeet2_contract_v1.json)、[演示脚本](docs/product/EffMeet2_演示脚本_v1.md)
- **历史归档**：[docs/archive](docs/archive/README.md)、[hardware/robot-design/archive](hardware/robot-design/archive/README.md)；归档中的 EffMeet2 是旧名，保留原始记录不改写

## 协作约定

- 不提交账号密钥、未经授权的会议录音、现场照片或个人信息
- 公共字段与契约变更先协商，再同步上下游；接口以 `contracts/v1/` 为准
- 未实机验收的能力不写成已完成；历史文档只代表当日状态
- 各模块先交独立自检与输入输出样例，再按阶段集成
