# 品牌替换执行报告 · 2026-10-21

- **执行日期**：2026-10-21
- **执行分支**：`feat/software-route-a-20261019`
- **执行目标**：将仓库 `D:\_wb_tmp\effmeet2_scan\EffMeet2` 文档口径中的旧品牌（EffMeet / EffMeet 2 / EffMeet2）统一替换为新品牌（正式中文品牌「在议」，正式英文品牌「effmeetbot」），仅修改 markdown 文件，不修改代码、文件名、目录名、图片路径、PDF 文件名，不执行 git commit。

---

## 一、执行概要

| 指标 | 数量 | 备注说明 |
|---|---|---|
| **扫描 Markdown 文件总数** | 200 个 | 排除 `.venv`, `.local`, `.git`, `node_modules`, `site`, `.agy-staff`, `dist` |
| **初始命中旧品牌词文件数** | 67 个 | 排除根目录 `README.md`（按指令由主控负责跳过） |
| **初始命中旧品牌词总数** | 178 次 | 大小写不敏感匹配 `effmeet(?:\s*2)?` |
| **修改文件数** | 24 个 | 均为 `.md` 文件，无任何非 `.md` 文件改动 |
| **总替换次数** | 26 处 | 仅针对人类可读叙述及文档主副标题，保持自然语境 |
| **剩余保留命中数（旧品牌）** | 152 处 | 全部属于受保护的白名单类别（环境变量、文件路径、代码标识符等） |
| **新品牌词命中（effmeetbot）** | 1 处 | 在作品提交名称中使用英文品牌，包含子串 `effmeet` |

---

## 二、修改文件清单与逐项替换明细（24 个文件，26 处替换）

### 1. `docs/product/参赛提交文案_2026-10-21.md`（2 处替换）
- **Line 9**（作品名称）：
  - **Before**: `EffMeet 2｜让线上成员坐回桌边的会议伙伴`
  - **After**: `在议（effmeetbot）｜让线上成员坐回桌边的会议伙伴`
  - **说明**: 对应“在议（effmeetbot）参赛作品”口径，字符数 29/30，满足官方表单限制。
- **Line 15**（作品简介）：
  - **Before**: `在线，不等于在场。EffMeet 2 是一台守在会议桌边的桌面机器人，帮线上参会的人重新"坐回桌边"。`
  - **After**: `在线，不等于在场。在议是一台守在会议桌边的桌面机器人，帮线上参会的人重新"坐回桌边"。`
  - **说明**: 对应任务示例 "EffMeet 2 是一台…" → "在议是一台…"。

### 2. `docs/product/EffMeet2_产品说明_v4.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet 2 · 产品说明 v4（定稿）`
  - **After**: `# 在议 · 产品说明 v4（定稿）`
  - **说明**: 文件名 `EffMeet2_产品说明_v4.md` 保留原样，仅改内文标题。

### 3. `docs/product/EffMeet2_判断样例与提示文案_v1.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet 2 候选判断样例与提示文案 v1`
  - **After**: `# 在议 候选判断样例与提示文案 v1`

### 4. `docs/product/EffMeet2_演示脚本_v1.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet 2 演示脚本 v1`
  - **After**: `# 在议 演示脚本 v1`

### 5. `apps/web/README.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet2 手机用户端`
  - **After**: `# 在议 手机用户端`

### 6. `apps/web-demo/README.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet2 手机用户端（本地演示版）`
  - **After**: `# 在议 手机用户端（本地演示版）`

### 7. `docs/archive/product/EffMeet2_报告修改指南_v2.md`（2 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet2 报告修改指南 v2（增量版）`
  - **After**: `# 在议 报告修改指南 v2（增量版）`
- **Line 41**（正文表单草稿）：
  - **Before**: `> 在线，不等于在场。EffMeet 2 是一款桌面会议机器人，帮线上的人"坐回桌边"：混合会议里...`
  - **After**: `> 在线，不等于在场。在议是一款桌面会议机器人，帮线上的人"坐回桌边"：混合会议里...`

### 8. `docs/archive/product/EffMeet2_总体整改方案_v1.md`（1 处替换）
- **Line 3**（文档主标题）：
  - **Before**: `# EffMeet2 总体整改方案 v1`
  - **After**: `# 在议 总体整改方案 v1`

### 9. `docs/archive/product/EffMeet2_整改核实记录_2026-10-09.md`（1 处替换）
- **Line 1**（文档主标题）：
  - **Before**: `# EffMeet2 总体整改方案：核实与实施记录`
  - **After**: `# 在议 总体整改方案：核实与实施记录`

### 10. `hardware/robot-design/README.md`（1 处替换）
- **Line 5**（主标题）：
  - **Before**: `# EffMeet2 · 机器人设计与采购统一入口`
  - **After**: `# 在议 · 机器人设计与采购统一入口`

### 11. `hardware/robot-design/round-yaw-v2/BOM.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 圆润转头版 · 硬件采购清单 v2`
  - **After**: `# 在议 圆润转头版 · 硬件采购清单 v2`

### 12. `hardware/robot-design/round-yaw-v2/TEST_GUIDE.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 圆润转头版 · 测试指南`
  - **After**: `# 在议 圆润转头版 · 测试指南`

### 13. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/README.md`（1 处替换）
- **Line 3**（主标题）：
  - **Before**: `# EffMeet2 · NOMI／布局A · v4工程候选`
  - **After**: `# 在议 · NOMI／布局A · v4工程候选`

### 14. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/SPLIT_PLAN.md`（1 处替换）
- **Line 3**（主标题）：
  - **Before**: `# EffMeet2 · 打印件拆分方案（交给建模接管方）`
  - **After**: `# 在议 · 打印件拆分方案（交给建模接管方）`

### 15. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/README.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 · NOMI布局A · v5拆件候选`
  - **After**: `# 在议 · NOMI布局A · v5拆件候选`

### 16. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 v6 · 安装手册 v5（2026-10-20 · v6r3 双修 + FACEFLAT + P33 + EDGEGRIP）`
  - **After**: `# 在议 v6 · 安装手册 v5（2026-10-20 · v6r3 双修 + FACEFLAT + P33 + EDGEGRIP）`

### 17. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY-图解版.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 装机图解 · 从零到开机（2026-10-20 修订版）`
  - **After**: `# 在议 装机图解 · 从零到开机（2026-10-20 修订版）`

### 18. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-PLAN.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 v6 · 合并同类项打印计划（print-ready · B 方案锁定）`
  - **After**: `# 在议 v6 · 合并同类项打印计划（print-ready · B 方案锁定）`

### 19. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md`（1 处替换）
- **Line 4**（适用范围说明）：
  - **Before**: `> 适用：EffMeet2 v6 打印执行（Bambu Studio + 学校 H2S/H2D/P2S + 自有 A1，PLA Matte 灰/黑）。`
  - **After**: `> 适用：在议 v6 打印执行（Bambu Studio + 学校 H2S/H2D/P2S + 自有 A1，PLA Matte 灰/黑）。`

### 20. `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/review-20261015/FEEDBACK.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 v6 问题处理反馈`
  - **After**: `# 在议 v6 问题处理反馈`

### 21. `hardware/robot-design/archive/seat-card-v1/BOM.md`（1 处替换）
- **Line 3**（主标题）：
  - **Before**: `# EffMeet2 席位牌方案 · 新版硬件采购清单`
  - **After**: `# 在议 席位牌方案 · 新版硬件采购清单`

### 22. `hardware/robot-design/archive/seat-card-v1/README.md`（1 处替换）
- **Line 3**（主标题）：
  - **Before**: `# EffMeet2 席位牌 · 封装布局 v1`
  - **After**: `# 在议 席位牌 · 封装布局 v1`

### 23. `hardware/robot-design/archive/legacy-enclosure/EffMeet2_外壳说明_v2.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet 2 外壳说明 v3（A 侧 · 2026-10-06 起，10-09 修订）`
  - **After**: `# 在议 外壳说明 v3（A 侧 · 2026-10-06 起，10-09 修订）`

### 24. `hardware/robot-design/archive/procurement/2026-10-09-original-shared-list.md`（1 处替换）
- **Line 1**（主标题）：
  - **Before**: `# EffMeet2 硬件采购清单（分享版）`
  - **After**: `# 在议 硬件采购清单（分享版）`

---

## 三、剩余命中清单及保留理由归类（共 152 处旧品牌命中）

根据任务约束，剩余 152 处 `EffMeet` / `EffMeet2` 命中严格受保护保留，分布在 56 个文件中：

### 1. 环境变量名（40 处保留）
- **规则要求**：`EFFMEET_*` 属于代码环境接口，严禁修改。
- **保留分布**：
  - `tests/acceptance/README.md`（14 处）：`EFFMEET_ACC_MIC`、`EFFMEET_ACC_WEB_OWNER`、`EFFMEET_ACC_ROBOT`、`EFFMEET_ACC_ONSITE_MIC`、`EFFMEET_ACC_MIC_SECONDS`、`EFFMEET_ACCEPTANCE_REAL`
  - `docs/archive/handoff/2026-10-05.md`（7 处）：`EFFMEET_DB_PATH`、`EFFMEET_TTS`、`EFFMEET_BENCH`、`EFFMEET_CONTROLLER_URL`
  - `docs/handoff/2026-10-20-machine-switch.md`（3 处）：`EFFMEET_TTS`、`EFFMEET_ROBOT_ID`
  - `docs/handoff/2026-10-19-software-route-a.md`（2 处）：`EFFMEET_ACC_MIC`
  - `docs/handoff/2026-10-20-esp32-bringup.md`（1 处）：`EFFMEET_ROBOT_ID`
  - `docs/archive/handoff/2026-10-05-final-handoff.md`（1 处）：`EFFMEET_DB_PATH`
  - `docs/archive/handoff/2026-10-06-A代做记录.md`（1 处）：`EFFMEET_TTS_RATE`
  - `docs/archive/handoff/2026-10-06-relay-TTS实现.md`（1 处）：`EFFMEET_TTS`
  - `services/relay/README.md`（1 处）：`EFFMEET_CONTROLLER_URL`
  - `apps/web/README.md`（1 处）：`EFFMEET_SQLITE_JOURNAL_MODE`
  - `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/README.md`（1 处）：`EFFMEET_REVIEW`
  - `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/README.md`（1 处）：`EFFMEET_SKIP_RENDER`

### 2. 文件/目录/图片/PDF/压缩包名称与链接目标（61 处保留）
- **规则要求**：文件/目录/图片/PDF 名称中的 EffMeet2 字样（含 markdown 链接目标）保留原样；不得声称 PDF 已改名。
- **保留分布**：
  - **PDF 文件名**（6 处）：`EffMeet2-装机图解版-20261020-v2.pdf`、`EffMeet2-装机图解版-20261021.pdf`、`EffMeet2-安装手册v5-20261020-r2.pdf`（在 HANDOFF.md、print-split-v6/README.md、装配实施方案.md 中）
  - **DOCX / ZIP 产物**（3 处）：`EffMeet2-重打件检验单-…-20261019.docx`、`dist/EffMeet2-初赛提交-20261021.zip`、`EffMeet2_赛事匹配与参赛建议.docx`
  - **3D 资产与图片**（16 处）：
    - `.blend` 文件：`EffMeet2_NOMI_布局A_v6_紧凑候选.blend`、`EffMeet2_圆润转头版_封装布局_v2.blend`、`EffMeet2_NOMI_布局A_工程候选_v4.blend`、`EffMeet2_席位牌_封装布局_v1_审阅.blend`、`EffMeet2_NOMI_布局A_v5_拆件候选.blend`、`EffMeet2_v6_面板三点固定_R1候选.blend`
    - `.glb` 模型：`EffMeet2_外壳_v3.glb`
    - `.png` 渲染与草图：`EffMeet2_NOMI方向_现有硬件_效果图.png`、`EffMeet2_白色脸颊_普通LCD_优化效果图.png`、`EffMeet2_测试草图_回收箱.png`
  - **Markdown 文件路径及链接引用**（34 处）：
    - `docs/product/EffMeet2_产品说明_v4.md`
    - `docs/product/EffMeet2_演示脚本_v1.md`
    - `docs/product/EffMeet2_判断样例与提示文案_v1.md`
    - `docs/product/EffMeet2_总体整改方案_v1.md`
    - `docs/archive/product/EffMeet2_总体整改方案_v1.md`
    - `docs/archive/product/EffMeet2_整改核实记录_2026-10-09.md`
    - `docs/archive/product/EffMeet2_报告修改指南_v2.md`
    - `docs/archive/product/EffMeet2_分工说明.html`
    - `docs/product/EffMeet2_论文依据与技术路径.html`
    - `archive/legacy-enclosure/EffMeet2_外壳说明_v2.md`
    - `hardware/enclosure/EffMeet2_外壳说明_v1.md`
    - `《EffMeet2-硬件采购清单-分享版.md》`（作为引用的旧文档文件名）
  - **证书与二进制**（2 处）：`.local/phone-qa-cert/effmeet2-qa-root.cer`、本地测试目录 `F:\素材1\eff2\EffMeet2-main`

### 3. 切片工艺预设名称与预设路径（34 处保留）
- **规则要求**：Bambu Studio 用户本地实存的工艺参数预设文件与预设继承名称不可变更，否则导致切片软件找不到预设或参数错乱。
- **保留分布**：
  - `EffMeet2-v6 0.20 H2S`
  - `EffMeet2-v6 0.12 H2S`
  - `EffMeet2-v6 0.16 H2S`
  - `EffMeet2-v6 0.20 H2D`
  - `EffMeet2-v6 0.16 H2D`
  - 路径 `%APPDATA%\BambuStudio\user\<id>\process\EffMeet2-v6 *.json`
  - 预设语境限定指代（如 `非你的 EffMeet 预设`）
  - 分布在：`SLICE-CARD.md` (9)、`PRINT-LESSONS.md` (7)、`HANDOFF.md` (5)、`PLATE-RUNBOOK.md` (2)、`PRINT-CARD-REPRINT.md` (2)、`PRINT-CARD-V6R3.md` (2)、`PLATE-CARD-P02P20.md` (2)、`PLATE-CARD-P15P17P26P29.md` (2)、`MORNING-PLAN.md` (2)、`cards/PRINT-CARD-REPRINT.md` (1)

### 4. 仓库名与 Git 远程 URL（4 处保留）
- **规则要求**：仓库名与 URL（`EffMeet2`、`github.com/eleanor-wsyy/EffMeet2`）属于仓库元数据，不得修改。
- **保留分布**：
  - `docs/archive/product/仓库导览_给D.md`：
    - `https://github.com/eleanor-wsyy/EffMeet2`
    - `git clone https://github.com/eleanor-wsyy/EffMeet2.git`
    - `cd EffMeet2`
  - `hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/review-20261016-measure/05_照片初判结果.md`：
    - `EffMeet2 仓库`

### 5. 硬件固件配置与网络凭据（9 处保留）
- **规则要求**：Wi-Fi SSID、密码、串口 REPL 提示符、NVS 命名空间等硬件运行参数。
- **保留分布**：
  - Wi-Fi SSID `EffMeet-Link`：`machine-switch.md` (2), `esp32-bringup.md` (1), `FIRMWARE_STATUS.md` (1)
  - Wi-Fi 密码 `effmeet88`：`machine-switch.md` (2), `esp32-bringup.md` (1), `FIRMWARE_STATUS.md` (1)
  - 串口配网 REPL 提示符 ``effmeet>``：`machine-switch.md` (1), `esp32-bringup.md` (1), `FIRMWARE_STATUS.md` (1)
  - NVS 命名空间 `effmeet`：`FIRMWARE_STATUS.md` (1)

### 6. 存储键与运行时标识符（4 处保留）
- **规则要求**：运行时系统标识、存储持久化 key、固件二进制名称。
- **保留分布**：
  - 前端 localStorage 键 `effmeet2.local.v1`：`apps/web-demo/README.md` (1), `docs/handoff/2026-10-19-github-app-review.md` (1)
  - LiveKit 房间参与者前缀 `effmeet-host-*`：`docs/handoff/2026-10-19-software-route-a.md` (1)
  - 临时导出目录 `/tmp/effmeet-web-next`：`docs/handoff/2026-10-19-github-app-review.md` (2)
  - 固件烧录二进制文件名 `effmeet2_robot.bin`：`FIRMWARE_STATUS.md` (1), `software-route-a.md` (1), `firmware/esp32/README.md` (1)

---

## 四、发现的矛盾表述与需要人工确认的歧义点

### 1. 比赛表单标题的署名形式（需人工确认）
- **现象**：在 `docs/product/参赛提交文案_2026-10-21.md` 第 9 行的比赛作品名称：
  原为 `EffMeet 2｜让线上成员坐回桌边的会议伙伴`。
  本次按品牌规则（“EffMeet2 参赛作品” → “在议（effmeetbot）参赛作品”）修改为：
  `在议（effmeetbot）｜让线上成员坐回桌边的会议伙伴`（共 29 字符，符合官方表单 ≤30 字符要求）。
- **人工决策点**：如果团队倾向在作品名称中省略英文直接使用纯中文简称，可将其微调为 `在议｜让线上成员坐回桌边的会议伙伴`（20 字符）。

### 2. 采购清单与旧文件名中的引用矛盾（已严格按规则处理）
- **现象**：`hardware/robot-design/archive/procurement/2026-10-09-original-shared-list.md` 是早期用户提供的采购清单副本。其一级标题修改为 `# 在议 硬件采购清单（分享版）`。
  而在其他 BOM 文档（如 `hardware/robot-design/round-yaw-v2/BOM.md` 第 11 行）中，正文陈述为：“本清单承接用户提供的《EffMeet2-硬件采购清单-分享版.md》”。
- **说明**：此处的“标题改在议、正文引用旧文件名保留原字样”严格契约了“文件/目录/图片/PDF 名称中的 EffMeet2 字样保留原样”的红线，避免出现代码/文件系统找不到文件的故障。

### 3. 旧历史外壳说明中的标题与 3D 产物名称
- **现象**：在 `hardware/robot-design/archive/legacy-enclosure/EffMeet2_外壳说明_v2.md` 中，文档一级标题已更新为 `# 在议 外壳说明 v3`；但第 14 行的 3D 模型产物名称依然保留为 `EffMeet2_外壳_v3.glb`。
- **说明**：3D 二进制资产文件名不可变更，标题已统一到新品牌口径。

### 4. 根目录 `README.md` 暂未变动（由主控负责）
- **现象**：根目录 `README.md` 按任务指令显式跳过，未作任何修改。目前根目录 `README.md` 仍包含 `EffMeet 2` 旧品牌字样。
- **后续协同**：主控在最终合并时需同步将根目录 `README.md` 替换为新品牌。
