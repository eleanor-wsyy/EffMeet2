# EffMeet2 手机用户端

主仓库用户端入口：`/app/`，代码位于 `apps/web/`；原主持人/台架工作台继续使用 `/`，没有被替换。实现基于已验证的 2026-10-07 用户端快照，2026-10-09 安全合入主仓库。

## 本机启动

在**仓库根目录**创建隔离环境并安装项目依赖：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-media.txt
./.venv/Scripts/python.exe scripts/run_participant.py
```

打开 `http://127.0.0.1:8765/app/`。脚本仅监听 `127.0.0.1`，不会向手机公网提供服务。使用 `scripts/seed_participant_demo.py --candidates 4` 创建明确标记为合成的演示会议；可用 `--port` 与 `--db` 隔离测试环境。不要提交会议数据、令牌或数据库。

## 已接通

- 入会表单、麦克风权限检查、会中原图与观点列表、底部候选确认、会中与观点地图横滑浏览、JSON 证据导出。
- 候选确认/拒绝、过期后仅本人主动重新校验、服务器 120 秒时限与版本检查；状态由后端回执驱动，不用假的倒计时或机器人动画。
- `/app/` 与 API 同源；原 `/` 工作台不改。刷新后可用邀请链接重新入会，已决定候选由服务端保持不可重复决定；短时断线保留最后画面，联网/回到前台后主动恢复现有单一轮询。
- PWA manifest、192/512 像素图标、iOS 主屏图标与仅作用于 `/app/` 静态壳的 Service Worker。可以在支持的 HTTPS 或 localhost 浏览器中安装；离线**只显示上次缓存的界面**，不能离线入会、读取会议证据、操作候选或导出新记录。API、认证和原图永不缓存。真实手机需要可访问的 HTTPS 部署，`127.0.0.1` 只代表当前设备。

## 需要独立联调和现场验收

- 目前只有本机 `remote_1`/`remote_2` 联调身份，昵称不是正式登录/鉴权；不能把本机预览称作公网产品。
- 麦克风按钮仅请求权限并立即停止轨道；LiveKit 发送、真实录音/上传和红点录音中状态未接通。
- 现场 AI 描述接口未提供时保持“暂无已保存的 AI 描述”；不以文件名或编造文字替代。
- 真实机器人播报、现场停顿安全、端到端音频链路，以及会议结束事件，必须由对应后端/设备接入并验证。本机模拟回执不代表现场播报。
- 仍需 iOS Safari、Android Chrome 的主屏安装/麦克风权限与 4G/弱网重连实机验收；在本机不能冒充完成。

## 测试

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests
node --test apps/web/tests/state.test.js
```

## 临时 HTTPS 真机演示

使用合成会议、单人身份和口令保护的本机隧道：详见 [手机验收说明](qa/README.md)。不要把本机调试 API 直接暴露公网；此入口不等于正式部署或机器人实播。

## 单一代码源与存储兼容

`apps/web/` 与根目录 `services/` 是唯一维护源；`用户端APP（10.7）/` 仅保留交付入口和历史恢复说明，不再复制整仓。UI 文案、样式与交互在本轮整改中未改动。

默认使用 SQLite WAL；只有 WAL 在事务开始前报只读错误时，才尝试切换当前数据库到 DELETE，并确认写事务能开始。不会重放已经开始的业务事务、延长候选 TTL，或影响其他数据库。真正的权限问题/其他进程占用仍可能失败，应检查权限和进程，而不是无限重试。

已知存储环境不兼容时，可在启动前显式配置（不是在浏览器中设置）：

```powershell
$env:EFFMEET_SQLITE_JOURNAL_MODE = "DELETE"
./.venv/Scripts/python.exe scripts/run_participant.py
```

该本机控制器维持单进程/单 worker；同数据库的短连接由进程内锁协调，跨进程仍依赖 SQLite 文件锁。真实设备投递不使用 mock 同步事务；真实网络副作用的 exactly-once 不能由这项修复保证。
