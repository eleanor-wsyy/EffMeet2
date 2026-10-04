# EffMeet 2

天猫 AI 黑客松「效率进化」方向的 AI 桌面会议伙伴。固定式机器人配合电脑伴侣应用与远程网页，围绕现场材料共享、本人确认后的观点提醒和可核对的会后记录设计产品体验。

## 产品方案与实施计划

- [论文依据与技术路径 HTML 报告](docs/product/EffMeet2_论文依据与技术路径.html)：产品形态、机内音频与 Wi-Fi、开源参考及改造映射、任务分工、实施步骤与参赛计划。
- [v1 接口契约 JSON](docs/product/EffMeet2_contract_v1.json)：统一数据格式、业务接口、媒体契约与合成测试样例。

当前报告版本：2026-10-04。文档用于方案规划与模块协作；正式产品不要求用户外接 USB 麦克风，USB 音频仅作台架测试。

### 阅读 HTML

GitHub 文件页显示源码。下载 HTML 后用浏览器打开即可离线阅读；接口契约已内嵌在 HTML 中。若需要同目录 JSON 链接，将两份文件下载到同一文件夹。


## 队友快速开始：各自在本机运行

仓库已公开，可直接克隆，不需要邀请协作者才能读取。每人的服务和SQLite数据库各自独立，**不会共享测试会议**；这不是多人联网会场。

```powershell
git clone https://github.com/eleanor-wsyy/EffMeet2.git
cd EffMeet2
```

也可以从GitHub下载代码ZIP，解压后在仓库根目录运行下面的命令。无需机器人、麦克风或模型账号。

## 无机器人也能跑：本地模拟闭环

已提供 FastAPI + SQLite 的本机调试应用。手工文本替代ASR，FakeAnalyzer替代模型，FakeRobot只记录模拟命令和回执，不发声音、不操作硬件。所有事件标为`mode=mock`。

### 启动（Python 3.11+，本次在 Windows / Python 3.13 验证）

在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/run_demo.py
```

macOS/Linux可使用相应命令（本次只在Windows/Python 3.13实测）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/run_demo.py
```

如果当前Python已经安装requirements中的依赖，可直接运行`python scripts/run_demo.py`。脚本默认仅监听`127.0.0.1:8765`，无需任何API Key。浏览器打开`http://127.0.0.1:8765`。

1. 新建会议，加入线上发言，选择“线上观点可能尚未获现场回应”并生成模拟结果：向现场提示的模拟执行次数仍为0。
2. 决定身份选“线上成员1”，点击“请机器人向现场提示”：模拟执行次数变为1，显示accepted → started → completed。
3. 点击“重试同一提示决定”：次数仍为1。同一请求复用已持久化结果。
4. 换“线上成员2”尝试替本人决定，或新建会议点击“不用向现场提示这条观点”：不执行。
5. 新建会议测试“线上观点已有现场回应”（先加现场回应）或“是否已获现场回应不确定”：不产生提示候选。
6. 生成原文记录，每项能定位到发言。记录只含原文观点，不伪造已达成的决议。

界面中的身份选择器是**本机测试身份**，所有本机调试者都能选择角色；它用于测试服务器的owner检查，不是商业产品登录系统。观点本人决定是否提示；提示接收方是现场成员。凭据仅存在本机进程/浏览器内存，不放URL。不能公开部署该模拟入口。不要把`127.0.0.1:8765`发给同学作为共享入口；它始终指向访问者自己的电脑，当前服务只允许本机访问。

### 验证

无需pytest；自动测试使用unittest，数据库在临时目录中：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# 先保持本地服务运行，再在第二个终端执行真实HTTP冒烟：
.\.venv\Scripts\python.exe scripts/smoke_demo.py
```

macOS/Linux执行测试时，把上面的`.\.venv\Scripts\python.exe`替换为`.venv/bin/python`。

HTTP脚本会建立新的合成测试会议，覆盖等待确认、确认及重试、拒绝、已有回应、不确定。不会调用云模型、录音或真实机器人。

### 模块与接口边界

- `contracts/v1/bundle.json`：代码使用的既有v1契约；与HTML内嵌及JSON文档快照有一致性测试。
- `services/controller/store.py`：SQLite账本、服务端seq、候选/确认状态、模拟执行与幂等、原文记录。
- `services/controller/fakes.py`：两个mock适配器。本轮模拟设备仅支持speak。
- `services/controller/app.py`：HTTP入口、测试会话、owner检查、错误响应；只接受本机Host/客户端和同源请求。
- `services/controller/demo.html`：B暂代的调试页，原生HTML/JS，无前端构建或外部运行资源。
- `fixtures/demo/closed_loop.json`：合成发言材料，可供C/D/E复用。

已实现的业务路由：创建会议、最终发言摄入、分析、本人决定、事件读取/after_seq恢复、生成/读取原文记录。调试专用`/api/demo/*`和`mock_status`查询参数不属于正式产品协议。原报告中的WebSocket、设备HTTP、媒体、图片等其余接口尚不在本轮范围；HTTP轮询不是WebSocket。

参数边界：候选120秒有效，过期后重新分析会更新待确认版本，旧版本不能执行；新发言进入后确认须重新分析；同一ID不同内容返回409；same-context分析重试复用候选。修正发言、真实回应判断、冷却策略和人工决议核对留给后续模块，当前摘要均标unresolved。

模拟完成回执只说明FakeRobot执行分支运行，不证明实际播放。mock在短SQLite事务内同步执行，**不能把真实设备/远程模型直接塞进这条事务路径**；后续需要持久化任务队列/worker、真实设备回执、安全停顿和取消机制。本轮禁止非mock适配器。

### 数据与后续交接

默认数据在`data/demo.sqlite3`，已被Git忽略。可在启动前设置`EFFMEET_DB_PATH`（相对路径按当前工作目录解释），无需删除旧数据库即可通过“新建会议”开始新场景。服务重启保留账本，不自动重放命令；浏览器刷新获取新测试会话凭据。

C可先按UtteranceFinal和样例接真实ASR；真实模型先产出AnalysisResult，再由控制器验证。D可用当前HTTP路由和mock场景独立做界面，正式账户与会议成员权限需另接。硬件接入始终是明确的新阶段，不由本机mock自动开启。

依赖版本记录在`requirements.txt`与`constraints.txt`，本轮另外在独立虚拟环境安装锁定依赖，核对全新环境运行；未修改系统Python。date-time格式校验所需依赖也已明确列入，避免缺失时静默放过非法时间。

## 协作约定

- 模块按报告中的目录边界和统一接口契约开发，公共字段变更先协商再同步上下游。
- 先交独立自检与共同输入输出样例，再按阶段节点集成。
- 正式报名人数与协助边界按赛事规则确认。
- 不提交账号密钥、未经授权的会议录音、现场照片或个人信息。
