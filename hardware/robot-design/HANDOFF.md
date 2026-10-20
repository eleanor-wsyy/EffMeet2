# 2026-10-20 · v6r3（P15/P26/P33）× FACEFLAT 合并落地 + 全仓同步

- **起因（10-19 晚实打）**：MG90S 塞不进 P15（尾端出线无让位）；摄像模组在 P26 里无保持结构。
- **v6r3 修复**（提交 `a3f4025`）：P15 尾端让位槽 6.8×9.6；**P26 重设计**（前壁 3.5、镜头入 P24 孔 0.5~0.7 导向、两 M3 背柱距 13.9）；**新增 P33 背板**（FPC 槽 6.4×2.5、压筋、2×M3×8 自攻）；FPC 跨距 10.75/余量 3.25。修复盘 `reprint-20261019-v6r3/`。
- **合并 origin/main**（`5471204`）：P23/P24 **FACEFLAT 大平脸**（106×96 R21、屏窗 62×46、116×116 R40 边框）＋ P15B（耳垫U槽孔底/底板盲孔）＋ P27/P28 RETAINFIX ＋ P29B EDGEGRIP 全部并入；**P15 双修合一**（让位槽＋U槽孔底/盲孔）。
- **摄像孔 4.2 风波**：`2d21bdc` 在 P15 提交里夹带把 6.8 改回 4.2（无设计说明），已**改回 6.8**；4.2 版 P24 盘件全部改名作废：`.SUPERSEDED-by-CAM68`（TMP-FIX-P24_BLACK_016 3MF/STL、P24_FACE_PANEL_FACEFLAT.stl）；**已打 FACEFLAT P24 钻 6.8**。P15B 盘件改名 `.SUPERSEDED-by-V6R3MERGED`（被合并版取代）。
- **件数 31→32**：P33 入 candidate 链（P32 编号保留给无源麦胶座，见 UNREGISTERED-PARTS）；`verify_v6_delivery.py` 已改 32。
- **同步动作**：parameters.json（FACEFLAT/6.8/跨距/32 件）、plate-registry 重生成＋RUNBOOK §6 新盘行、parts_img 全量重出（含 P33）、INTERFACE_GATES 状态刷新（LCD-01 已实测、FACE-01 压配定案、CAM-01 v6r3）、thinwall 审计七件改动件 **FAIL_THIN 0**（`production/thinwall-v6r3.json`）、SLICE-CARD/UNREGISTERED/MEASUREMENTS/ASSEMBLY §1.4/§3.3/§7/§8 同步。
- **重建校验**：32 件 overlap 0、containment 全过、yaw 三姿态 0、`verify_v6_delivery.py` **PASS**；改动 STL 恰好 P15/P23/P24/P26/P27/P28/P29＋新增 P33，其余字节不变。
- **apps/web 保持功能版**：main 的 `apps/web` 即 `apps/web-demo`（演示版）内容，合并时功能版未动。
- **⚠️ 待办**：队友的 `EffMeet2-重打件检验单-…-20261019.docx/pdf` 里 P15(WIREFIX)/P26 节已过时（被合并版/v6r3 取代），需要按 `reprint-20261019-v6r3/PRINT-CARD-V6R3.md` 重出检验单；10-20 打印包 `today-20261020/`（P23 灰＋七合一黑盘）。
- **固件（他人提交）**：`dfe7f27…3161d0b` 五个提交——串口检测/烧录脚本、LAN 网关+设备 token+UART 配网、WS2812 状态灯、MG90S 舵机驱动、INMP441/MAX98357A I2S 驱动（REPL 台架命令）、WS 握手/DHCP 修复。**实机烧录与拾音/播放回执验收仍 NOT_RUN**。

---

# 2026-10-19 · P15/P17/P26/P29 修复盘 v2 + P24 摄像孔 6.8

- **返工原因**：P15 舵机口袋 12.5+0.6 太紧；P17 功放单柱/板低；P26 镜管 4.6 装不进 6.5 镜头；P29 核心板槽 2.1 太松。修复：P15 口袋 **13.7**；P17 两 M2 柱 **12.6**；P26 镜管 **6.5**；P29 槽 **1.8**。
- **P24 漏改已补**：`CAMERA_APERTURE 4.2→6.8`（`camera_lens_d+.3`）；`candidate-stl/P24` 已重出 **v6r2 77×45 + Ø6.8**；**旧 P24 打印件钻 6.8**；`plates-merged/P24_v6r2_77x45.stl` / B1p-v2 仍是 4.2 旧版。
- **盘 v2**：P26 已转 90°（镜管朝床）；P15/P17 **局部树支撑 5%**（P15 z15–16/20–21；P17 z7–8 托盘外沿）；P29 brim5/支撑关；黑料先烘干。盘卡 [PLATE-CARD-P15P17P26P29.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/plates-merged/PLATE-CARD-P15P17P26P29.md)。
- **源→导出已同步**：`build_v6.py` + blend 重出；`candidate-stl` 31 件重导；`PARTS.csv`/`parts.json`/`export-byte-audit` 更新；P17 12.1、P24 6.8、P26 6.5、P15 13.7、P29 1.8；`verify_v6_delivery.py` **PASS**。
- **仍差**：P24 旧打印件钻孔；P15/P17 支撑预览；黑料烘干；P24/P25 版本陷阱。

---

# 2026-10-18 · P03/P05/P06/P28 重打成功 + 支撑方向收口

- **实打成功配方**：P03 翻转（顶部减重孔朝下）；P05/P06 **保持原向**；树支撑 5% + 分支 2mm + 顶距 0.2 + 界面 1；P06 底部 38.5 孔加 **Ø34×1.0 支撑阻挡器**；P28 单盘 **10mm brim**、不支撑。文件 [reprint-20261018/](../../reprint-20261018/)，设置卡 [PRINT-CARD-REPRINT.md](../../reprint-20261018/PRINT-CARD-REPRINT.md)。
- **P26 背后方孔 = `CAMERA_FPC_EXIT`（6×10×8）**，给 14mm 摄像头 FPC 出线；不是缺陷、不重打。镜头孔 Ø4.6 对 P24 的 Ø4.2。
- **版本**：`candidate-stl/P24/P25` 是旧 **80×45**；补打只认 `plates-merged/P24_v6r2_77x45.stl` / `P25_v6r2_77x45.stl`；P01 只认 `P01_v6r3_tolerant_usbc.stl`。
- **教训 37–47 已入 [PRINT-LESSONS.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md)**：支撑方向、P02 接缝、P20 立柱、P28 brim、配合台账、打印前 60 秒自检。

---

# 2026-10-17 · 读到实存预设：P20 病因定位收口（教训31 变铁证 / 墙层数彻底排除）

**执行入口：[SLICE-CARD.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/SLICE-CARD.md)（已按本轮证据重写）＋ [PRINT-LESSONS 教训34–36](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md)。**

- **发现本机装有 Bambu Studio 02.06.00.51**（`D:\Program Files\Bambu Studio`），此前"本机无 Bambu、无法切片"的边界**部分作废**：
  - `--info` 可用，**独立印证 P20 几何无罪**：`manifold=yes`、`number_of_facets=1236`、`36.000×14.000×8.600002`、`volume=1752.106689`（与 manifold3d 的 1752.108 一致）。
  - `--slice` **仍不可用**：H2S 与 A1 两种机型预设下均段错误 `0xC0000005`，崩在 `update_values_to_printer_extruders_for_multiple_filaments`（预切片之后、导出之前）→ **拿不到 G-code**。故"支撑是否真长进 P20 的孔"**仍无法离线证实**，只能靠 GUI 预览。
- **读到用户实存预设（决定性证据）**：`%APPDATA%\BambuStudio\user\959069435\process\EffMeet2-v6 *.json`，沿 `inherits` 解析生效值：

  | 预设 | 保存时间 | `wall_loops` | `enable_support` | `support_on_build_plate_only` |
  |---|---|---|---|---|
  | `EffMeet2-v6 0.20 H2S`（**INTERN2-DEC 用**） | **2026-10-15 16:06:23** | **6** | 1 | **0（未自设，继承默认）** |
  | `EffMeet2-v6 0.12 H2S`（BNIGHT2 用） | **2026-10-16 09:13:26** | **4** | 1 | **1（已自设）** |

  → **10-16 的对症修复只存进了 0.12 预设；0.20 H2S 预设此后从未重存**，至今 `wall_loops=6`+`sbpo=0`。P20 从黑盘(0.12)挪到灰盘(0.20)用的正是没被修过的那个。**教训31 由推断升级为文件级事实。**
  其余生效值：`wall_generator=classic`（非 Arachne）、`detect_thin_wall=1`、`outer_wall_line_width=0.42`、**`inner_wall_line_width=0.45`**、`line_width=0.42`、`sparse_infill=gyroid 15%`、`support_top_z_distance=0.25`、`support_threshold_angle=35`。
  **键名坑**：是 `enable_support` 而非 `support_enable`；写错会解析成 `None` 而误判"支撑没开"。
- **墙层数彻底排除（我自己的工具也算错过一次）**：`thinwall_audit.py` 早先用**单一 E=0.42** 套 `(2k-1)E`，把 P20 的 2.20mm 环壁算成 `k_max=3`/残隙 0.0979mm/"4.3× 过挤"。但 Bambu classic 生成器**第1圈用外墙宽、第2圈起用内墙宽**：`d₁=0.5×外`、`d_k=外+(k-1.5)×内`。用真实双宽（0.42/0.45）重算 → **k_max=2、残隙 0.91mm（gap fill 接管）、CLEAN/OK**；第3圈 `d₃=1.095` > 半厚 1.10，只剩 0.005mm 退化脊线会被丢弃。
  **故 wall_loops 设 6/4/2 对 P20 结果相同**（都只生成 2 圈）——这解释了用户"改成 4 也没用"：**不是预设没重存的问题，是墙层数根本不是病因**。工具已改 `--eouter/--einner` 双参数 + 退化脊线过滤，全 31 件重跑：**空层 0、FAIL_THIN 0**（P20=OK、P04=OK、P21/P22/P24=OK）。
- **嫌疑重排**：①**挤出/耗材（首要）**——照片是"3 件停在互不相同高度＋断口粗糙"，任何切片设置都造不出这种形貌；灰卷含水**从未实测**，教训25 只证明了黑卷受潮。②**支撑范围 sbpo=0（确凿预设偏差，该修，但未必是缺孔主因）**——按几何 P20 的 6.4×6.4 口袋朝上开口、Ø2.6 是竖直通孔，**两者都不构成悬垂**，理论上不需要支撑。③墙层数/薄壁/建模：**已排除**。
- **本轮未改任何几何**：`git status` 实测改动的 `.stl`/`.3mf`/`.blend` = **0 个**。Ø7→Ø6.8 的建模提议已撤回（无依据）。**要重打的就是原 `candidate-stl/P20_TACTILE_HOLDER_UNVERIFIED.stl`**（1236 面、36×14×8.6、已归零、朝向正确、@0.20 = 43 层）。
- **状态纪律不变**：stage=reversible_blockout；三放行布尔 false；26 项 NOT_RUN；`slicer_status` 仍 **NOT_RUN**（CLI 切不出，未产生任何切片证据）。

---

# 2026-10-16 晚 · P20「圆孔打不出来」排查（结论：几何无罪，两次误判已更正）

**执行入口：[SLICE-CARD.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/SLICE-CARD.md)（照着点的一页）＋ [PLATE-RUNBOOK §6 盘登记总表](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md) ＋ [PRINT-LESSONS 教训30–33](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md)。**

- **症状**：INTERN2-DEC 盘（H2S-07，App 报 128/128 层「成功」）实物 5 件里 3 件只有下半截、断口粗糙、停在互不相同高度；P20 轻触托座两个 Ø7 柱的 Ø2.6 孔「永远打不出来」，已失败无数次。用户实证：**墙层数从 6 改成 4 后照样失败**。
- **结论：模型/盘/朝向/壁厚全部无罪，不要改建模。** 实测（新工具 `tools/thinwall_audit.py`，manifold3d 逐层偏移腐蚀＋形态学开运算，E=0.42/lh=0.2）：
  - P20：`genus=2`（两孔全程贯通）、**空层 0**、`k_max=3`、墙心残隙 **0.0979mm**、thin_frac **0.00%**、1236 三角面（盘内与 `candidate-stl/` 逐面一致）、朝向 36×14 面朝下柱朝上（正确）。3 圈墙＋0.098mm 残隙**接近理想**（两对面墙珠子搭接即填满，band<E 不产生空洞），**不足以让 Ø2.6 孔消失**。
  - 全 31 件：空层 **0**、`k_max≤1` 的层 **0**、thin_frac 最大 **1.53%**（P28）、FAIL_THIN **0** 件 → 整套 v6 几何没有任何薄于一道挤出的特征。
- **两次误判已更正（原文均保留＋更正并列）**：
  1. **教训22/30 的「墙层数过多→整层丢弃」机制不成立**：墙层数设得比几何能容纳的圈数大，生成器只是**不生成多余圈**，不会丢层；且 `6×0.42=2.52` 只算单侧墙，环壁是内外两侧同时生成，k_max 由 `W=(2k-1)E` 决定（2.20→k=3）。**这就是「改 4 没用」的真正原因——墙层数从来不是病因。** 墙层数 4 保留（够用无害），但别再当病因调。
  2. **教训26/HANDOFF 的「P04 4896→1266」量纲错误**：见下节更正。
- **最强嫌疑（未证实，须现场预览确认）＝支撑长进孔/口袋**：RUNBOOK:85 早已诊断过同一个件——「NIGHT 四废（P04/**P20**/P21/P22）病根＝**支撑长进口袋/孔洞**＋压圈立打」，对症设置是「**支撑生成位置＝仅在打印板生成**」。但那条**只写在 BNIGHT2 一行**，§2 全局表与 §5 参数段都没有，而 **INTERN2-DEC 在 RUNBOOK 里根本没有条目** → P20 从黑盘挪到灰盘后修复就丢了，每次换盘都从零猜设置。**已修**：该设置上升到 §2 全局表，并补 §6 盘登记总表（17 盘全覆盖，「无条目不许上机」）。
- **次强嫌疑＝挤出/耗材**：照片形貌是「断口粗糙＋多件停在不同高度」，属**挤出中断**（堵头/料尽/湿料气泡）而非切片缺层（后者断口平整、顶面规则层纹）。叠加教训25（黑卷受潮已确认）→ **灰卷也应复测含水**，别因「灰卷之前没犯」就排除。
- **硬线索：实际工程 ≠ 仓库盘。** App 报 **128 层**，但 INTERN2-DEC 最高件 14.4mm／0.20 层高只有 **72 层**；`plate_registry.py --match 128` 反查**无任何盘×常用层高＝128**。**排查前必须先把 Bambu 里那个工程另存 3MF 入仓**，否则所有分析都对不上实物。
- **新增可复现工具（本机离线核对，非切片器）**：`tools/thinwall_audit.py`（薄壁/空层，补既有三关盲区：delivery-validation 只查 closed+正体积、export-byte-audit 只查 watertight+零面积面、教训22 截面审计只查「该层面积是否为 0」，**都量不到「特征做不做得出来」**）；`tools/plate_registry.py`（盘内容＋层数指纹＋无源件检出）；`tools/decimate_planar.py` 重写（三角面自校验）。产物：`production/plate-registry.json`、`production/decimate-audit.json`。
- **无源件立专账**：`P32_HOLDER_L/R`（麦胶座）与 `P18T_CRADLE`（USB-C 容差托架）**不在** build_v6.py／v6 blend（374 对象无匹配）／candidate-stl／PARTS.csv，只活在 3MF 内部 → 不可参数化重出、无法追溯。见 [UNREGISTERED-PARTS.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/UNREGISTERED-PARTS.md)（**不进 PARTS.csv**，因 finalize_exports.py 会重写它）。附带查出命名漂移：同一 224 面托架在三盘里叫三个名（`P18_TOLERANT_CRADLE`/`P18T_TOLERANT_CRADLE`/`P18T_CRADLE`）。
- **未做（有意）**：①**不改 P20 建模**——曾提议柱 Ø7→Ø6.8 凑 2.10mm 阶梯，实测证明无依据，撤回；②**不擅自覆盖** `decimated/P02_decimated.stl`（13614 面，已用于打 G3p-DEC 盘，脚本默认拒绝覆盖，需 `--force`）；③**P04 真减面未做**——DISSOLVE 对其无效，须换能删内部顶点的方式（COLLAPSE/remesh）并重新过教训26 阈值，且 P04 是 GT2 带轮、齿形属功能面，改动需先确认；4896 三角面对 34mm 带轮是否真算「过密」也未验证。
- **状态纪律不变**：stage=reversible_blockout；三放行布尔 false；26 项 NOT_RUN；本次新增工具与文档**不构成任何打印/制造放行**，`slicer_status` 仍 NOT_RUN（本机无 Bambu Studio，未实际切片）。

---

# 2026-10-16 · 打印收尾+装配启动（湿黑料确认/减面整改/手册v3/学妹交付）

**当前执行入口：[ASSEMBLY.md v3](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md)（去抽象+测试用具+图鉴）＋ [PLATE-RUNBOOK §5](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md) ＋ [MEASURE-TODO v3](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/MEASURE-TODO.md)。**

- **湿黑料确认**：BNIGHT2 再炒面+满床拉丝，灰卷不犯 → 黑卷受潮。处置：黑卷烘干45–60℃4–6h+拉丝测试；内部件全改灰（INTERN2）；黑只留外露 P14/P28（BVIS 直打版 + BVIS-TILT 斜打实验版，老师建议斜打试运气，需筏层+树支撑）。
- **机房老师整改**：过密网格致切片周长路径过密/内部碎填充 → P02 平面融解 18134→13614 面（1.5°，vol d0.077%）、P04 4896→1266（5°，vol 0.000%）；新盘 G3p-DEC / INTERN2-DEC；已打 P01/P23（4.1万/6.0万面）返工时用减面版。澄清：截面≤2.5mm 的全墙件打实心是设计正确（P28/P27/P25/P13/P32壁/P14管壁/P20柱环）。
  > **⚠️ 2026-10-16 晚更正（原文保留）：P04 那条不成立。** 「4896→1266」是**拿 STL 三角面数比 Blender 多边形数**——DISSOLVE 只把共面三角形并成 n-gon（4896 三角面→1266 个多边形），而 **STL 只存三角形**，导出重新三角化后**仍是 4896**。实测（`tools/decimate_planar.py --dry-run`，Blender 4.5.3）：P04 @5.0° **三角面 4896→4896（0%）**、dVol 0.0002%、dBbox 0 → 判 `NO_TRI_REDUCTION`，**减面是彻底 no-op**；`decimated/P04_decimated.stl` 与 `candidate-stl/P04_DRIVER_32T_UNVERIFIED.stl` 逐面相同，INTERN2-DEC 盘内 `P04_DRIVER32T_dec` 也是 4896 面。**机房老师反映的「网格过密」对 P04 从未解决**（vol 0.000% 那半句是对的）。
  > **P02 那条成立**：@1.5° 三角面 **18134→13614（−24.93%）**、dVol 0.0775%、dBbox 0，入仓产物可复现、正确。
  > 另：旧 `decimate_planar.py` 的 OUT 指向已失效的会话临时目录，产物从未真正入仓；已改为 `plates-merged/decimated/` 并加三道自校验闸（三角面无下降／超阈／落盘面数不符 → 均不产出可信产物）。详见 [PRINT-LESSONS 教训26 更正](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md)。
- **学妹交付归档**：[review-20261016-measure/](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/review-20261016-measure/)。直尺数字全废（±0.5 判不了公差，她也没填）；照片定性销账 3 项（ZZ盖/TIANKONGRC MG90S/4Ω3W钢印）+ 设计坑 1 个（**INMP441 含焊盘总宽17–18 > 板径14** → P21/P22 作废、P01 壁袋环弃用、新件 P32 胶座腔19）。待补：卡尺10组+补拍8组（★底面拾音孔特写）。
- **装配启动（周末窗口）**：学校周末关门；宿舍 A1 打 PETG 替身颈/滑片（NECK-PETG-A1 盘）供合婚联调；供电走核心板 Type-C；缺件替代法见 ASSEMBLY §0 表。10-21 初赛前联调窗口=本周末。
- **状态纪律不变**：stage=reversible_blockout；三放行布尔false；26项NOT_RUN；替身/容差件不构成放行。

---

# 2026-10-15 · 打印已开打（B方案：灰并行 / 黑单盘）＋待测清单

**当前执行入口：[v6 PLATE-RUNBOOK §2026-10-15](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md) ＋ [待测清单](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/MEASURE-TODO.md) ＋ [打印教训集](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md) ＋ [安装手册](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md)。** 以下为本日事实记录。

- **v6r2 重建完成（LCD 四孔实测）**：孔径4/横77/纵45（取代80×45假定）、Type-C未突出、镜头凸4、玻璃-PCB4 已回填 MEASUREMENTS.csv。`build_v6.py` `lcd_boss_rect=(77,45)` 在隔离副本以 Blender 4.5.3 重建，逐件 diff 其余28件 0.00% 漂移。新 P23/P24/P25 → [plates-merged/](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/plates-merged/)，新增盘 **G1灰0.16(P23)**、**P25灰0.20**、**B1p-v2黑0.16(+P24)**；旧 B1p 作废改名 `.SUPERSEDED-by-v2`。
- **已开打**：学校 H2S 打 `TMP-B23p-SAFE`（灰0.20，11件）；H2D 先 `TMP-G3p`（灰0.16，P02上盖）后改 `TMP-THINP25`（灰0.16，P16+P25+4干净管）；H2S 黑卷 `TMP-B1p-v2`/`TMP-Bsmall`。可打印 3MF 在 [plates-merged/](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/plates-merged/)。
- **B方案（用户定）**：黑料仅1卷→只有外露件 B1p 用黑；机构/支架件按 RUNBOOK"可灰"改灰，用闲置第2卷灰并行。原 plates/ 的 G1/G2/B1/B2/B3 六盘被 plates-merged 取代（未删，仅取代）。
- **薄壁发现（重要）**：切片报"空层无法打印"的 **P07–P10 层间支柱、P16 扬声器托架**，经逐Z三角面跨距验证**网格无真空层**；P07–P10 实为环状导出网格隐患，已用**解析干净管**（OD8.2/ID3.4/h11.4，体积497.7与理论吻合）替换；P16 改杯口朝上；THIN 与 P25 合并为 `TMP-THINP25_GREY_016`（小件层时变长反而更稳）。
- **预设注入不可行**：外部写入 `%APPDATA%/BambuStudio/user/<id>/process/` 的预设 .json/.info 会被 Bambu 启动时删除。复用预设只能 UI「保存为预设」（已存 EffMeet2-v6 0.20 H2S / 0.16 H2D）。切片参数手设，简中标签：**墙层数**(=6)、**稀疏填充图案**(=螺旋体)、**开启支撑**、**顶部Z距离**(=0.25,需开支撑+高级才显示,可跳过)、**检查薄壁**、**床温**(在耗材·纹理PEI行·首层/其它层)。喷嘴须 **0.4**（H2S 默认0.2会隐藏0.4基预设）。
  > ⚠️ **10-16 更正**：上行「墙层数(=6)」已过期，现行＝**4**；且实测证明墙层数设大**不会丢层**（生成器只是不生成多余圈），它不是缺特征/空层的病因。现行完整口径见 [v6 PLATE-RUNBOOK §2](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md)（新增：墙生成器 Arachne、检查薄壁开、**支撑「仅在打印板生成」**）。
- **待测**：全量见 [MEASURE-TODO.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/MEASURE-TODO.md)。A组（LCD四孔/Type-C/镜头）已测完回填；B/C组等到货。
- **空层警告真凶更正（重要）**：墙层数6×0.42线宽=2.52mm 塞不进薄特征（2.4壁/2mm柱/1.6唇）→切片整层丢弃→上半悬空炒面。**全局墙层数改4**（或墙生成器Arachne+检查薄壁）。已存预设（0.20H2S/0.16H2D）内含6，改4后须UI重存覆盖。manifold3d 逐层截面审计全件 clean，历次警告均非网格病。
  > ⚠️ **10-16 二次更正：本条的机制解释不成立**（原文保留）。用 `tools/thinwall_audit.py` 对全 31 件逐层实测：空层 **0**、`k_max≤1` 的层 **0**、thin_frac 最大仅 1.53%。①墙层数设得比几何容纳圈数大**不会丢层**；②`6×0.42` 只算单侧墙，环形壁由内外两侧同时生成，k_max 由 `W=(2k-1)E` 决定（2.20→3、2.40→3）。**仍成立的是**「空层警告≠网格坏」这个方向；真机制是**薄于一道挤出的薄鳍在「检查薄壁」关闭时被整片丢弃**（且 P07–P10/P16 已因 10-15 的修复而测不出薄特征）。详见 [PRINT-LESSONS 教训22 更正/教训30](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PRINT-LESSONS.md)。
- **今晚最终队列**：H2S-A=G2NIGHT(P01杯体v6r3+P11重打)→G3p；H2D=G1头壳→COUPON样片；H2S-B=NIGHT→**BNIGHT2（7件黑0.12质量档：P14翻面/P04/P20/P28/P21P22平躺/P18T容差托架）**。交接时 BNIGHT2 尚未开打。
- **新手测量指南**：[MEASURE-GUIDE.md](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/MEASURE-GUIDE.md)（图文PDF在outputs）交大一学妹执行到货测量 B1–B7/C1–C7；回表后回填 MEASUREMENTS.csv 并触发对应件重建/试配判定。
- **清理与可复现**：plates-merged 9 个作废盘移入 `_superseded/`（git 历史可溯，未硬删）；`build_v6.py` 参数同步 v6r3（lcd_boss_rect=77×45、后USB-C容差窗13.5×9.5），仓库源现可复现 v6r2/v6r3 全部 STL。
- **平行工作流（同日远端提交）**：v6接口复核/采购清理与[面板三点螺钉固定R1候选](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/review-20261015/face-retention-r1/)独立于 canonical v6；实物操作按 [INTERFACE_GATES](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/INTERFACE_GATES.md)。**R1 是否合并须先过局部几何检查+接口样片；本打印线当前仍用 canonical P24（77×45 v6r2）**，两线不混打。
- **状态纪律不变**：stage=reversible_blockout；三个放行布尔false；26项测试NOT_RUN；本次开打为候选件试打，不构成打印放行。

---

# 2026-10-15 · v6接口复核与采购口径清理

- 当前v6/A2模型和31件STL未替换。唯一BOM §12已清理旧布局、TP4056必买、v5 41件/跨轴FPC/长螺钉数量；新增E17预算输入板，SKU仍未选。原订单物流未新核实。
- 实物操作按[v6接口门槛](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/INTERFACE_GATES.md)推进。LCD孔位/堆叠、USB-C板、GT2/舵机、跨轴细线和脚垫均不伪填实测。
- [面板三点螺钉固定R1候选](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/review-20261015/face-retention-r1/)独立于canonical v6；是否合并须先过局部几何检查和接口样片。不用胶/强过盈/脆性卡扣替代承力连接。
- z=2mm底部空间与C07脚垫预算相符，尺寸图区分名义0基准与裸实体高度。
- manufacturing_ready / hardware_validated / final_design_approved保持false；26项硬件测试NOT_RUN。

---

# 2026-10-13 · v6紧凑候选（布局A2，当前第一入口）

**当前模型/件表/STL改看 [v6 README](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/README.md)。** 以下10-12各节为历史。

- **v5 G1头壳/G2杯体已停打作废**（用户决定）；v5不再打印。
- **布局A2**：摄像头FPC实测仅**14mm**（禁止裁剪/加长），故**核心板＋摄像头＋屏进头部**；麦／功放／扬声器／舵机／停止键仍固定底座，**麦不随头转**（BOM C06不变）。跨轴只剩约9根细软线穿Ø22轴孔；E05取消，E04改头内杜邦线。
- **尺寸**：整机180×164×222 → **153×139.4×200.8**；头宽150→132；底座为v4剖面×0.85。
- **不装**扩展板（实测95×87×12放不下）、电池、TP4056（推迟到路线B/决赛）；Demo外供5V≥2A经后部USB-C输入小板（未选型）。
- **传动2:1**：MG90S→32T→64T，GT2 **188mm**闭环6mm，C=44.84；舵机±90°→头±45°。
- 已实测：核心板（元件高6、排针8、USB-C与FPC座在远离模组端）、屏（PCB85×50、总厚11、四孔、排针在FPC侧短边）、摄像头（8×8×4）、扩展板。麦/功放/扬声器/舵机/轴承未到货，按采购页尺寸建模，回填[v6测量表](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/MEASUREMENTS.csv)。
- 检查（名义几何）：5外壳 0非流形/0边界/1块；31件两两重叠0、与代理重叠0；三姿态旋转组与固定组重叠0；31个STL闭合正体积。**未切片、未样片、未实装。**
- **下一步**：到货实测回填 → 屏四孔/玻璃深度锁定 → 重建 → 切片 → PETG样片验配合 → 正式PLA打印。
- **打印按盘执行**：每盘一个 3MF＋总表见 [v6 PLATE-RUNBOOK](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md)（6 盘 256 起点排布，未切片；样片先行）。
- **状态纪律不变**：stage=reversible_blockout；三个放行布尔值false；26项测试NOT_RUN。

---

# 2026-10-12 晚 · 打印已启动＋今晚下单口径（已被10-13 v6取代；G1/G2已停打作废）

- **打印进行中**：**G1 头壳**（学校 **H2S**，层高 0.16，Brim 仅外侧 5mm）＋**G2 杯体**（学校 **H2D**，层高 0.20）已上机；其余 4 盘＋样片待打。盘×机器×特殊设置见 [v5 PLATE-RUNBOOK](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/PLATE-RUNBOOK.md)。
- **采购按 [BOM §12.0](round-yaw-v2/BOM.md#final-purchase-decision) 七区执行**：✅ 已下单（GOOUU 套装；PLA Matte **灰×2 已到货**、**黑×1 已下单未到货——勿重复下单**）；🔴 必买（INMP441×2 / MAX98357 / TP4056）；🔴 要买（扬声器 / 6806×2 / MG90S / 五金线材）；🟡 先翻库存（Type-C 线×2 / 5V 电源 / 舵机稳压 / 轻触开关）；🟡 第二批别买（E04/E05 / GT2 带 / 3.7V 锂电）。
- 学校喷嘴为**硬化钢 0.4mm**；PLA 干燥为“建议非强制”（受潮按官方 45–70℃ 档，不是 80℃）。旧 `stl/` 草案已删除。

---

# 2026-10-12 · v5真实拆件候选交接（历史，当前按v6/A2）

**当前模型和打印清单改看 [v5 README](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/README.md)。** 已按SPLIT_PLAN v1.1补承力/传动/模块支架/导向/声管/线夹，生成41件独立候选。不要再按v4“内部都是代理、尚未拆件”的历史描述重复工作。

- 三类工作：保留并增加接收的外观5件；补真正机构/支架/夹持件；导出逐件候选STL、件表及几何预排3MF。
- 盘数不冻结。6张几何起点盘不是切片工程；逐件朝向/支撑必须实际切片＋PETG/正式PLA样片，空白记录不填PASS。
- 核心板、固定布局A、两只INMP441、MAX98357A、TP4056、普通矩形屏与NOMI外观方向不变。扩展板未测不纳入。
- v5电池(53,0,14)、功放(20,-34.3,25)、充电板(-40,32,16)是避开支架的候选覆写；未据此改写v4旧fit报告。
- 唯一采购仍BOM§12。M09补标准螺母与M3×70样品；不强制热装嵌件、不复制第二份BOM，不按未核齿形/带长盲买。
- 原生.blend及修改器保留；旧EFFMEET2_PACKAGING_V1/R2/Scene/N4对象快照不变。导出只取真实打印件，采购代理与KEEP_OUT不导出。
- **状态纪律不变**：stage=reversible_blockout；final_design_approved/manufacturing_ready/hardware_validated=false；26个硬件测试仍NOT_RUN。
- 到货后：先回填[v5测量表](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/MEASUREMENTS.csv)及唯一parameters → 同步源接口 → 重建模型/导出/渲染/审计 → 再切片/实打/安装。只改JSON不会自动重建全部机械关系。

以下v4及以前内容保留追溯；遇到拆件状态冲突，以本节和v5件表为准。

# 2026-10-11 · 圆润转头版建模与采购交接

# 2026-10-12 · 会话收尾：当前状态与下一步

> **本节是给下一位接手者的第一入口。** 下面「v4最新执行更新」及以前各节保留为背景与追溯。

## 一、已经定案的事（不要再讨论、不要回退）

| 项 | 定案 | 何时 |
|---|---|---|
| 参赛路线 | **路线 A**（电脑伴侣承载本地 AI）；路线 B 是决赛范围 | 10-11 冻结 |
| 布局 | **A2：核心板＋屏＋摄像头进头部；麦/功放/扬声器/舵机/按键固定底座不随头转**（2026-10-13，摄像头FPC仅14mm所致；原布局A作废） | 10-13，功能倒推 |
| 主板 | **GOOUU ESP32-S3-CAM**（带 OV3660） | 10-12 |
| 材料 | **PLA Matte 灰 / 黑**（实验室禁 ABS/ASA；A1 亦无腔温） | 10-12 |
| 美学 | **NOMI 球头 + Ø106 圆黑脸 + 矩形屏窗 + 暖白弯眼 + 短颈 + 鹅卵石底座** | 10-11 |

**作废不得复活**：微雪板（归档）、Korvo 基线、ABS-GF、圆屏/AMOLED、透明罩、喷漆、布局 B。

## 二、采购状态

**✅ 已下单**
- **GOOUU 套装**：核心板 + OV3660 + 扩展板 + 2.8″TFT，**¥86.5**，次日达
- **PLA Matte 灰 ×2（已到货）；黑 ×1（⚠️ 已下单、未到货——不要再下一单）**

**🔴 今晚下单**（分区表见 [BOM §12.0](round-yaw-v2/BOM.md#final-purchase-decision)）
- 必买：**INMP441 ×2、MAX98357、TP4056**（GOOUU 无板载音频/电池管理）
- 要买：扬声器 4Ω/3W、**6806 轴承 ×2**、MG90S 舵机、M2.5/M3 五金、线材接插件
- 先翻库存：Type-C 数据/供电线、5V/≥2A 电源、舵机独立稳压、轻触开关
- 第二批（今晚别买）：E04/E05 跨轴线束、GT2 带、3.7V 锂电（等实物/规格）

## 三、已交接出去的工作

**建模、渲染、打印件拆分 全部交由建模接管方执行。**

📄 任务书：[**打印件拆分方案**](round-yaw-v2/revision-20261011-nomi-layoutA/SPLIT_PLAN.md)

内含：硬件现状 · 打印工作室现状 · 建模现状（v4）· 拆分任务清单 · **合盘策略（分组原则，盘数待件表冻结）** · 拆分铁律 10 条 · 拆完仍需实测 9 项 · 参考文件 9 份

**当前拆分现状**：v4 只拆出 **5 件外观件**（头壳/面板/短颈/上盖/底座杯，且 `part_graph_status=provisional`）；
**机构件全是 PROXY/ENVELOPE**（轴承座×2、带轮×2、空心轴、滑盖、键帽），**舵机架/线夹/声学通道/限位/电子支架无独立件**。

> 2026-10-12 更新：以上是交给接管方**之前**的 v4 状态；v5 已交付 **41 件独立候选**（见文首节与 [v5 README](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/README.md)），不要再按本段描述重复拆件。

## 四、下一步（按顺序）

1. **收货** → 卡尺实测：核板完整排针/双USB/元件最高点/实际孔位（不假定四孔）/Type-C凸出、**扩展板外形**、屏玻璃/PCB/厚度/**J2针序**、OV3660模组与FPC、INMP441/MAX98357/TP4056模组、MG90S耳孔/舵盘、6806公差、电池/扬声器/接头
2. **下单时让客服确认**：2.8″TFT 的驱动 IC（ST7789 / ILI9341）
3. **回填 `parameters.json`** → 更新 v4 生成源 → 重建模型与证据（**不用旧报告给改动后的件背书**）
4. **跑样片**：S1 配合样片（PETG @ 自有 A1）定公差档 → S2 正式料样片（PLA Matte）验收缩/孔径/表面
5. **拆分执行**（接管方）→ 按 SPLIT_PLAN §五 合盘切片
6. **打印（进行中）**：学校已开打 **G1 头壳（H2S）/ G2 杯体（H2D）**；余盘按 [PLATE-RUNBOOK](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/PLATE-RUNBOOK.md)：A1 打 G3 上盖＋B1/B2/B3 小件＋样片
7. **装配与 26 项实机验收**（TEST_RECORD_TEMPLATE 全 NOT_RUN）

## 五、打印工作室现状（本会话新查证）

| | 内容 |
|---|---|
| **学校** | 广州美术学院 实验教学中心**模型实验室**：拓竹 **P2S×8 + H2S×10 + H2D×10 = 28 台** + 高精密激光切割机×2 |
| **关键限制** | ⚠️ **通风不允许 ABS/ASA**（后期改造才放开）——**这是改用 PLA 的直接原因** |
| 喷嘴 | 通用 **0.4mm（硬化钢）**；**0.2mm 需自备**；需预约审批 |
| **自有** | 拓竹 **A1**（256³，非封箱）+ 现有 PETG |
| **材料规则** | 全件同一种料；PLA **按实际机型和材料配置；受潮仍须按厂商参数干燥**；⚠️ 热变形约 55℃，禁暴晒 |
| **分工** | A1：样片 + 全部黑料小件；学校：三件灰料大壳并行 |

## 六、状态纪律（不得违反）

- `manifest.json` 的 `stage=reversible_blockout`、`final_design_approved=false`、`manufacturing_ready=false`、`hardware_validated=false` **保持不变**
- 26 项测试模板**全部 NOT_RUN**，不得标 PASS
- **禁止裁剪 FPC**；**禁止生成伪装成放行件的 STL**；不把网格改后缀冒充 STEP
- 未实测项一律标 `unverified`

---

## v4最新执行更新（已合并GOOUU套装定案）

**扩展板未测，不纳入放得下的结论；不得另买微雪屏。当前是核心板直连候选＋外置音频／充电模块，电池独立供电与完整GPIO尚未放行。**

- 当前可编辑模型／10张实渲／3张图纸入口：[NOMI布局A-v4](round-yaw-v2/revision-20261011-nomi-layoutA/README.md)。Screw、Boolean、Lattice、Solidify及头部姿态依赖保留，旧v2场景／文件未改写。
- 参数已同步到GOOUU62.6×28.3核心板及INMP441×2／MAX98357A／TP4056模块、套装2.8屏预算占位、双6806／传动／电池预留、Ø106圆脸、14mm真实间距、3.2mm头底接收和阶梯D接收。**不再是“CAD未改、仅AI图”。**
- 当前主板GOOUU，灰／黑PLA Matte；不回到微雪、Korvo、ABS-GF、圆屏、透明罩或喷漆。布局A／固定麦／电脑伴侣路线A不变。
- 采购只看33项[BOM§12](round-yaw-v2/BOM.md#final-purchase-decision)：屏SKU需两端接口核准，摄像模组不重复买；新增电池与实际前部状态引出纳入同一BOM，不再散落互相矛盾。
- **撤回旧“现场裁剪FPC”和多余跨轴信号。** 禁止裁排线；只有显示线束和CAMERA排线跨轴，舵机／按钮／灯／主板供电均固定。
- 安装、打印、测试与README已同步。**旧 stl/ 草案已于 2026-10-12 删除**（避免误当打印包）；`build_print_parts.py` 保留为历史源，不用于生成 v4 件。
- 五外壳网格／十五预留盒／三姿态的检查属于名义几何范围；承力固定座、电子支架、齿形／轴向锁定、滑盖导向、实物配合、FPC50循环和固件／实机验收尚未放行。manifest的manufacturing_ready／hardware_validated仍false，模板全部NOT_RUN。
- 下一位AI先读v4 README、[ENGINEERING_REVIEW](round-yaw-v2/revision-20261011-nomi-layoutA/ENGINEERING_REVIEW.md)，再改唯一parameters.json及v4生成源；不要用旧6项fit-report宣称新结构已验证。

> **⚠️ 2026-10-11 更新，优先于本文其余全部内容。**
> ① 主板选型 **已定：GOOUU ESP32-S3-CAM（带 OV3660）+ 布局 A**（见「已定案」节）；采购以 BOM §12 为准。
> 　　**[BOM 第12节](round-yaw-v2/BOM.md#final-purchase-decision) 已定案：GOOUU `ESP32-S3-CAM`（带 OV3660）+ 布局 A**（§12.1 末段、§12.2 E01）。**采购一律按 BOM §12 执行；Korvo 基线已作废，微雪方案已归档。**
> ② 「可打印CAD化交接」节的材料与面罩口径**已作废**，以 [BOM 第12节](round-yaw-v2/BOM.md#final-purchase-decision) 与 [PRINT_PLAN.md](round-yaw-v2/PRINT_PLAN.md) 为准。
> **旧节正文保留用于追溯，不再作为采购、建模或固件依据。**

## 给接手成员和AI的结论

从仓库README进入hardware/robot-design/README.md，再读本文件、round-yaw-v2/BOM.md与round-yaw-v2/README.md。**当前设计方向是圆润转头版，阶段为可逆封装布局；没有最终外观批准、打印放行或实机转头验收。** 本次工作是设计与资料整合，不是固件和软件功能上线。

**读本文其余部分前，先确认三件事：**

1. **参赛 Demo 交付走路线 A**（电脑伴侣承载本地 AI），路线 B（去电脑化、机器人直连云端）**不是本次初赛交付范围**。
2. **主板已定：GOOUU ESP32-S3-CAM（带 OV3660）+ 布局 A（板在底座，麦克风固定不随头转）**，采购以 [BOM §12](round-yaw-v2/BOM.md#final-purchase-decision) 为准。**该板无板载音频，须配 INMP441×2 / MAX98357 / TP4056**，见 [GOOUU-BOARD-SPEC](round-yaw-v2/GOOUU-BOARD-SPEC.md)。布局 B 已归档，不得复活。
3. **材料与面罩口径**以 [BOM §12](round-yaw-v2/BOM.md#final-purchase-decision) 与 [PRINT_PLAN.md](round-yaw-v2/PRINT_PLAN.md) 为准，其余旧节仅供追溯。
4. **接手顺序**：本文件 → [BOM.md](round-yaw-v2/BOM.md) → [PRINT_PLAN.md](round-yaw-v2/PRINT_PLAN.md) → [模型说明](round-yaw-v2/README.md)。

## 2026-10-11补充：路线A/B定义（已冻结，不再讨论）

> **本节转述仓库既有定义，不是新决策。** 权威原文见根 [README.md](../../README.md) 第 5 行与 [产品说明 v4](../../docs/product/EffMeet2_产品说明_v4.md) 第 46 行。

**产品形态分两路线：**

| | 路线 A（**当前参赛 Demo**） | 路线 B（最终产品形态） |
|---|---|---|
| 后端承载 | **电脑伴侣应用**承载本地 AI（FunASR + 千问候选 + 事件账本） | **机器人 Wi-Fi 直连云端**，去电脑化 |
| 用户端 | 需电脑在环 | 仅需平板或手机 |
| 机器人角色 | 端（拾音 / 推流 / 播放 / 动作） | 端（同上） |

**两条路线的 AI 都不在机器人本机上运行。** 差别只在"本地电脑 vs 云端"这一层，**不在算力、也不在是否跑固件**。

**对本次交付的约束（重要）：**

1. **初赛（10.21）交付走路线 A。** 路线 B 属最终产品形态，是决赛（11.5–11.8 杭州 48H）的攻关范围，**不是本次提交内容**。
2. README 第 22 行明确：路线 A（Demo）**不要求用户外接 USB 麦克风，USB 音频仅作台架测试**。
3. → **板载 AFE / AEC 不在初赛交付的关键路径上**。这不代表声学不重要（T07/T08/T17 与 AEC 边界仍是 TEST_GUIDE 的实机项），而是说：初赛演示不阻塞于板端声学调优。

## 已定案：主板 GOOUU ESP32-S3-CAM，布局 A

> **2026-10-12 更新**：主板由微雪 ESP32-S3-CAM-OV3660 **改为 GOOUU**，并**已下单套装「核心板+OV3660+扩展板+2.8寸TFT」¥86.5**（次日达）。
> 原因：微雪那块国内拿货要等（官方店海外链路），赶不上 10.21；GOOUU 次日达。
> **代价**：GOOUU 无板载音频（无麦/无编解码/无功放/无电池管理），须外接 **INMP441×2 + MAX98357 + TP4056**。
> **布局 A 不变**（板在底座、麦克风固定不随头转）——注意麦改为 **INMP441 模块**，位置仍由我们定在底座上缘。
> 规格、尺寸（**62.6×28.3mm**）、引脚见 [GOOUU-BOARD-SPEC](round-yaw-v2/GOOUU-BOARD-SPEC.md)；微雪评估归档于 `archive/waveshare-board-eval-20261012/`。


> **决策：GOOUU `ESP32-S3-CAM`（带 OV3660）+ 布局 A（板在底座）。** BOM §12 已同步，采购以 BOM §12 为准。

**布局 A 的定义**：主板、电源、3.7V 电池、扬声器、舵机全在底座；头部只留 LCD＋摄像头，靠 **E04/E05 两条跨轴 FPC** 连接。**麦克风固定在底座、不随头转。**

**为什么是 A 而不是 B**（功能倒推，不是省事）：

1. **拾音是产品命脉**——整条链是"现场说话 → 麦克风 → ASR → 千问判断 → 证据 utterance_id"。麦随头转会让拾音特性随头角变化，**ASR 准确率变成头部朝向的函数**，而机器人转头的时刻恰是最需要稳定拾音的时刻。
2. **B 会推翻既有产品规则**（`BOM.md` C06）：「麦克风不随头转，不能宣称通过转头实现指向性拾音」。
3. **宠物形态**：A 头轻（腔内只有 LCD＋相机）→ 转得快、稳、不啸叫；B 头重 → SG90 吃力。
4. **代价性质不同**：A 的代价是工程努力（两条排线 + 过轴寿命验证），B 的代价是产品功能缺陷（拾音不稳，修不了）。

**A 的唯一风险与消解**：E04/E05 需扛连续 50 次 ±45° 转。
→ 使用完整端接、针序／间距／接触面一致的合适长线或厂家组件，禁止裁剪FPC；只在允许半径内宽缓走线，不赌定长件到货；过轴通道做成可换小支架；过轴寿命是 `TEST_GUIDE` 现成验收项。

**布局 B（整板进头部、麦随头转）已归档**至 `archive/layout-candidates-20261011/`，不再维护、不得据此采购或建模。

### 换板后必做（付款后立即启动，BOM §11.7）

- [x] **主板规格 —— 已取得**：GOOUU 板体 **62.6×28.3mm**、全 GPIO 表、必配外接件，见 [`round-yaw-v2/GOOUU-BOARD-SPEC.md`](round-yaw-v2/GOOUU-BOARD-SPEC.md)
- [x] **已下单**：GOOUU 套装（核心板+OV3660+扩展板+2.8″TFT）**¥86.5**
- [ ] **仍缺（到货卡尺实测）**：板实测长宽高、**扩展板尺寸（决定用不用扩展板）**、镜头突出量、Type-C 凸出量、屏针脚顺序、INMP441/MAX98357/TP4056 模块外形
- [ ] **下单时让客服确认**：2.8″ TFT 的驱动 IC（ST7789 / ILI9341）
- [ ] 确认板载双麦与 ES7210 的**通道 / 回声参考接法**（麦在底座，不随头转）
- [ ] 屏模块：驱动 IC、分辨率、可视角度、反光
- [ ] 镜头突出量 vs 头部预留盒（现假设 24×16×20mm）；**镜头开孔坐标由实板决定**
- [ ] Type-C 凸出量 vs 底座侧面浅凹槽
- [ ] **AEC 重测**（换板必做；初赛路线 A 不阻塞，**决赛 11.5 前必须完成**）

### 不要宣称

- 不宣称换板后 AEC 与 Korvo 等效——芯片组相同（ES7210/ES8311/NS4150B）不等于声学结果相同，必须实测；
- 不宣称 E04/E05 的过轴寿命已验证——必须实跑 50 次循环；
- 不宣称布局 B 的任何结论可用——已归档；
- 不修改 `manifest.json` 的状态字段：`stage` 保留 `reversible_blockout`；`manufacturing_ready` / `hardware_validated` 保持 false。

## 2026-10-10最新外观要求：NOMI方向＋组装同步

用户再次明确参考NOMI，保留现有硬件/转头/少操作打印方案。新的[效果图](round-yaw-v2/concept/nomi-aligned-20261010/EffMeet2_NOMI方向_现有硬件_效果图.png)采用球头与圆黑面板，里面仍为普通矩形LCD；之前小横窗/大白脸颊候选不作为当前方向。

新增[外观/组装同步说明](round-yaw-v2/EXTERIOR_ASSEMBLY_REVISION.md)，并同步ASSEMBLY_GUIDE、PRINT_PLAN、TEST_GUIDE及BOM入口：面板接收、屏/相机可拆支架、先穿线后封头、内藏颈间隙、声孔/按键和对应复测。物料ID/数量与核心选型不增加；parameters.json/.blend尚未执行新接口改造，仍无打印/实机放行。

## 2026-10-10补充：安装与测试文档

新增[安装指南](round-yaw-v2/ASSEMBLY_GUIDE.md)、[测试指南](round-yaw-v2/TEST_GUIDE.md)及[26项记录模板](round-yaw-v2/TEST_RECORD_TEMPLATE.csv)。安装按裸板→机构→活动线→入壳；实机验收包括50循环、30分钟运行、本人确认/真实回执、实体停止及AEC边界。模板全部NOT_RUN，缺CAD/接线/固件记BLOCKED。文档不是已执行测试或可装配CAD，manufacturing_ready/hardware_validated保持false。

## 2026-10-10补充：每项部件负责什么

当前[BOM第10节](round-yaw-v2/BOM.md#component-functions)已逐项解释全部30个部件的具体功能、直接效果和最终验收目标，并补充板载器件分工与整机闭环。物料数量、尺寸、采购状态及模型未改变；目标描述不代表已经实机通过。

## 2026-10-10最新决策：打印优先、少操作

用户要求减少操作与耗时。当前取舍以[BOM第12节](round-yaw-v2/BOM.md#final-purchase-decision)和[PRINT_PLAN.md](round-yaw-v2/PRINT_PLAN.md)为准：**A1 PETG关键样片→H2S灰/黑 PLA Matte正式件→去支撑直接螺接装配**；不安排PC壳喷漆、激光切透明窗、PAHT-CF/PPA-CF批次或机加工必需件。打印黑框露出LCD自身屏面，接受可见矩形窗口和细层纹；不承诺AI整片玻璃脸/注塑光面。

机构优先国产标准6806尺寸级轴承＋位置舵机样品，先锁实物和配合，再打印；现有SG90能用于台架，新购MG90S不自动等同更安静。轴承座、轮毂、带轮、支架尽量打印，电子/轴承/软带/线束/密封仍买现成。

> ⚠️ 下节（「可打印CAD化交接」）中**PA6-CF / PPA-CF / TPU 95A / 喷漆 / 激光切面罩**等原始讨论均已作废，**采购与建模一律以 BOM §12 + PRINT_PLAN + 本文顶部各「2026-10-11 补充」节为准**，下节仅保留几何缺口与分阶段做法。

bottom_z=2不是2mm底厚、0.2喷嘴不能盲用于玻纤料、单喷嘴支撑与上盖尺寸等修正见PRINT_PLAN第3节。当前CAD仍是封装布局，制造/实机状态不升级。

## 2026-10-10补充：可打印CAD化交接（待Codex接手）

### 目标与边界

用户决定：**为“去学校用 H2S 一次性打印外壳”做前置准备**，先完成**可打印 CAD 化**。此事**尚未开工**，本文只记录缺口、约束与已定决策，**不改变阶段**：仍为 `reversible_blockout`，仍无 STL/STEP 放行、无最终外观批准、无实机验收。

**已确认的可用设备**（来源：用户自有 + 学校实验室设备清单照片，OCR 读取）：用户自有拓竹 **A1**；学校实验室另有 **Bambu Lab P2S、H2S、H2D** 及**精密激光切割机（含 4 轴）**。设备与材料差异、工艺分配见 BOM 第 11.8、11.9 节。

### 已定的两个决策

1. **外壳路线：H2S 整件打印**（接缝最少、孔径补偿最好）；理由与 7 条整件打印约束见 BOM 11.9。
2. **耗材：PLA Matte 统一，裸打哑光**（⚠️ **2026-10-11 更正，覆盖本条原始内容**）：
   - 外观件（头壳、底座杯体、上盖）：**PLA Matte 灰**；
   - 面罩框、短颈、内部支架、轴承座、舵机架、轮毂连接盘、带轮、滑盖、按钮帽、线夹：**PLA Matte 黑**；
   - 柔性件改为**采购现成工业片材**（闭孔硅胶 / EPDM 声学垫片、约 2 mm 硅胶防滑片，刀切即可），**不打印 TPU**——`TPU 95A` 不自动等于软密封泡棉；
   - **一律螺钉连接**，不设计必须弹性变形的薄卡扣（PLA 较脆）；采用螺钉、圆角与受力肋；
   - **不喷漆、不打磨、不退火、不切透明板**。接受均匀细层纹与玻纤哑光质感；不接受大支撑疤、拉丝、缺层、翘边、装配需强砸。
   - 喷嘴 **0.4 mm 普通**（官方更推荐 0.6；若 0.4 样片堵塞或不稳定则换 0.6 并**重测配合**）；PLA **吸湿性低于 ABS/PA、拆封即可打**，但**受潮时仍须按拓竹官方 PLA 干燥参数处理**，不得当作免干燥材料。
   - 两色**分批**打印，不做一件多色反复换料。依据：BOM §12.1、PRINT_PLAN §1/§5/§6。

   <details>
   <summary>本条 2026-10-10 原始内容 —— <b>已作废，仅供追溯</b></summary>

   - 受力/装配件：PA6-CF 或 PPA-CF（必须 H2S/P2S，A1 无腔温不支持）；
   - 外观件：PETG / ABS 或打磨喷漆的 PA6-CF；
   - 柔性件：TPU 95A；
   - 碳纤料外观为哑光纹理，要达到接近注塑质感必须后处理喷漆，属工时。

   **作废原因**：用户 2026-10-10 晚反馈"能打印则打印、少点操作、时间有限"，BOM §12 据此**取消 PAHT-CF / PPA-CF / PC / TPU 整卷采购与喷漆工序**，统一为 PLA Matte 裸打。**以 BOM §12 为准。**
   </details>

3. **第一趟先用自有 A1 打 PETG 验证件**（用户已定）：验证几何、分件与开孔，失败成本低、可快速迭代；**不消耗工程料，不占用学校 H2S**。A1 打 PETG 属官方“适合”档，无需腔温。
   - ⚠️ **PETG 试片结论不能跨材料套用**：PETG 与 PLA Matte 收缩率不同，**配合孔、轴承座、滑槽必须在正式材料上重新验证**；且**不能用缩比样件验收安装孔，必须 1:1**。
   - ✅ **机器无门槛**：PLA Matte 不需腔温/硬化嘴/烘干，学校 H2D/H2S 与自有 A1 均可打；分工按 PRINT_PLAN §4.5（小件 A1、三件大壳学校并行）。

### CAD 可打印化的实际缺口（给建模接手人）

当前 `build_round_yaw.py` 生成的是参数化草模。经阅读该脚本，现状如下：

**几何基础（可复用）**
- `BASE_CUP` / `BASE_LID`：单一径向剖面 + 原生 Screw 360°，剖面为闭合轮廓，`use_merge_vertices` 已开，旋转后为闭合实体；
- `HEAD_SHELL`：Sphere − 内球 − 底面 − 面罩开口，Boolean solver 已为 `MANIFOLD`。

**必须解决（否则打不出/装不上）**
1. **无实体化与真实壁厚**：头壳壁厚目前只是内外球半径差（约 2.4 mm 的数值差），导出前须确认为**闭合单流形实体**，而不是两层面片；Boolean 结果需检查非流形边与自交。
2. **底座底厚仅 2 mm**（`bottom_z=2`）：直径 164 mm 的 2 mm 底会严重翘边，须加厚或加肋。
3. **无安装结构**：`parameters.json` 的 `unverified` 第 5 条（bearing SKU / motor mount / transmission ratio / head receiver / hard stop）全部未定，因此**轴承座、安装柱、连接盘、卡扣、螺钉孔、分件口无法定尺寸**；这些是 S2 阶段的阻塞项。
4. **无功能开孔**：出声孔是 `SPEAKER_PORT_POSITION` 位置代理、无真实穿孔；**麦克风孔不存在**；面罩/屏窗、摄像孔、按钮孔均未完成。当前壳体打出来是**听觉全封闭**的。
5. **代理件必须排除**：所有器件 proxy（MAINBOARD/LCD/CAMERA/SERVO/BEARING/SPEAKER）与 `KEEP_OUT_*` 线框盒**不得进入导出网格**（KEEP_OUT 为 `hide_render` wire，误导出会变成实心块）。
6. **打印公差未定**：`unverified` 第 8 条（thermal, tipping stability, print tolerances and fasteners）未定，孔的公差与收缩补偿无法冻结。

**建议的分阶段做法**（避坑）
- **先做 S1+S3**：实体化 + 真实壁厚 + 补功能开孔（出声孔、麦克风孔、按钮孔、屏窗开口），产出一个**"能打、能装、能出声"的验证壳**；
- **S2（安装结构）等轴承/舵机/传动选型锁定后再补**，否则会把猜测尺寸固化进打印件，打完即废；
- **S4**：分件（头壳单体、底座杯体、上盖、短颈）、收缩补偿、导出 STL/STEP。

### 打印件清单（第一趟：自有 A1 + PETG 验证）

**A1 尺寸余量已核**（成型 256×256×256）：头壳 150×128×144（余 106 mm）、底座杯体 180×164×78（余 76 mm）、上盖 ~152×152×10、短颈 Ø46×25 —— **四件均可整件打印**，但底座 180 mm 接近 A1 热床有效区，须留边距并注意翘边。

待打的 C01 类壳体件：头壳、底座杯体、上盖（带 48 mm 转轴孔）、短颈（带 22 mm 线孔）；细件含滑盖、按钮帽、LED 导光窗。

> ⚠️ **面罩工艺已变更（2026-10-11）**：原「面罩/屏窗走激光切割亚克力/PC、不打印」**已作废**。
> C02 现改为 **打印黑色 PLA Matte 面罩框**＋**LCD 自身屏面直接露出**（中部为真实矩形贯通显示窗），
> **取消 PMMA/PC 透明板切割与额外透明保护盖**。依据 BOM §12.1、PRINT_PLAN §2。
> 取舍代价：矩形显示区与窗口接缝可见，失去独立透明保护盖——这是缩短工序的明确代价，须接受。

**验证件打前须落实**：CAD 须先完成 S1（闭合单流形实体、真实壁厚）与 S3（出声孔、麦克风孔、按钮孔、屏窗开口），否则打出来的是全封闭壳体，无法验证听觉与装配。**先打关键配合件（轴承座、连接盘、卡扣）验证孔径，再打头壳/底座大件。**

### 不要宣称

- 不宣称已有可打印/可装配 CAD，或已完成 STL/STEP 放行；
- 不宣称装壳后声学可用（出声孔/麦克风孔尚未完成）；
- 不把本节的设备能力、材料建议当作已采购或已上机验证；
- 不改变 `manifest.json` 的 `stage`、`manufacturing_ready` 等状态字段。

## 本次具体更新

1. 按用户“可转、圆润、参考NOMI”的反馈，从席位牌方向改为球面头部＋短颈＋固定底座；保留旧方案供追溯。
2. 用用户指定的银河智算Image2生成主视觉。它是独立AI概念图；实际建模尺寸和细节与概念图不逐像素锁定。
3. 新建可编辑Blender封装布局：主板移到底座，LCD/摄像头随头转，独立轴承与偏置SG90留位，扬声器前向。外包络180×164×222 mm；各尺寸与假设见parameters.json。
4. 编制30项BOM，划分电子件、转头机构、外壳/声学；标注数量、位置、采购状态、核验问题和官方依据。
5. 复核并修正旧清单中的LCD V1.1资料、摄像接口针数及扬声器“官方禁止8Ω”的未经核实归因；保留旧文件但明确降为历史。
6. 将分散的assets/enclosure、hardware/enclosure和采购文档归到hardware/robot-design，补充根README、handoff导航及旧路径跳转。根目录之外不维护第二份BOM。

**2026-10-11 追加：**

7. **修正材料与面罩口径冲突**。原「可打印CAD化交接」节仍写 PA6-CF/PPA-CF + TPU 95A + 喷漆 + 激光切割透明面罩，与 BOM §12 直接矛盾；现将旧口径折叠标注作废，正文统一为 **PLA Matte 灰/黑 裸打哑光 + 打印黑色面罩框**，并补充 H2S 不可约时的 PETG @ A1 降级路径。
8. **主板选型已定案：GOOUU `ESP32-S3-CAM`（带 OV3660）+ 布局 A（板在底座、麦克风固定不随头转）**，BOM §12 已同步。Korvo-2 基线作废；微雪方案归档；布局 B 已归档不得复活。
9. **补入路线 A/B 权威定义**，并明确初赛（10.21）走路线 A、板载 AFE/AEC 不在初赛关键路径——这是**评估**换板代价的前提之一，不是「换板已决定」的依据。
10. 补充「当前不要宣称」条款，覆盖换板等效性、换板已定、路线 B 范围、作废材料口径与「全部仍为计划状态」。

## 读哪些文件，分别说明什么

| 文件 | 事实/证据边界 |
|---|---|
| [BOM.md](round-yaw-v2/BOM.md) | 采购建议，不是已付款清单、现货保证或实购兼容性证明 |
| [parameters.json](round-yaw-v2/parameters.json) | 官方板形尺寸与假设厚度/预留分别标注；假设需实物确认 |
| [fit-report.json](round-yaw-v2/fit-report.json) | 6项预留盒在解析腔体内、同舱盒分离；不含真实线束、传动和声腔 |
| [yaw-clearance.json](round-yaw-v2/yaw-clearance.json) | 5°步长检查左右45°刚性头壳与底座的竖向间隙；不是完整碰撞/寿命检查 |
| [evaluated_mesh_validation.json](round-yaw-v2/production/evaluated_mesh_validation.json) | 实际评估的占位网格无非流形边及零面积面；不等于生产拓扑放行 |
| [yaw-dependency-audit.json](round-yaw-v2/production/yaw-dependency-audit.json) | -45/0/+45姿态中布尔控制随头转、壳体闭合且体积基本不变 |
| [validation_report.json](round-yaw-v2/production/validation_report.json) | 综合为WARN，列出未完成的受力、接收、传动与安装接口 |
| [stage_state.json](round-yaw-v2/production/stage_state.json) | 仍停在blockout，等待外观反馈，不得把状态改为生产完成 |

检查产生于本次建模阶段。此次目录迁移和脚本路径整理不算新增机械验收；没有重新跑软件回归测试，也没有修改控制器/网关/前端/固件业务代码。

## 已修复并留存的建模问题

- 旋转剖面最初多出一条无面轴线边，已从Screw源剖面移除；初始诊断留存。
- 头壳布尔控制最初没有随头转，极限姿态会切坏外壳；已统一父级，左右极限检查通过。失败截图和检查点只留本地，团队默认看renders/review-02及“修订”三姿态图。
- 新模型保留旧场景作为快照；默认场景为R2_ROUND_YAW_BLOCKOUT。旧.blend原文件未被改写。

## 当前不要宣称

- 不宣称SG90已稳定带载、达到NOMI的噪声或顺滑度，或可连续360°。
- 不宣称模型能直接打印装机；没有STL/STEP生产导出。
- 不把普通GPIO按钮说成硬件断麦。
- 不把AI图的屏幕、孔阵、按键、滑盖当作已完成的结构设计。
- 不把转头时间轴当固件功能；firmware/esp32当前只有README骨架。
- 不把采购搜索词/搜索页当已核验商品；不按预留盒直接采购同尺寸轴承。
- **不宣称换板后 AEC 与 Korvo 等效**——芯片组相同（ES7210/ES8311/NS4150B）不等于声学结果相同，必须实测。
- **不宣称路线 B 属于初赛交付范围**；初赛（10.21）走路线 A。
- **不按旧节材料口径下单或建模**（PA6-CF / PPA-CF / TPU 95A / 喷漆 / 激光切割透明面罩）——均已作废。
- 不宣称已采购、已到货或已上机验证；本目录至今**全部为计划与文档状态**。

## 下一步交接事项

| 工作接口 | 需要先落实 | 完成证据 |
|---|---|---|
| **可打印CAD/建模接手人（待Codex）** | 见上节“可打印CAD化交接”：S1实体化+真实壁厚、S3功能开孔先行；S2安装结构待轴承/舵机/传动选型锁定后再补 | 闭合单流形实体；分件STL/STEP；**第一趟 A1+PETG 验证件**的装配与开孔记录；**未完成前不得称可打印放行** |
| 结构/建模协作人 | 头壳方案反馈；轴承SKU、头部重量/惯量、受力连接、传动比、线孔、限位、安装孔与公差 | 实物图纸＋可装配模型＋受力/转角与夹线试验；角色仅为建议，不覆盖团队现有分工 |
| 硬件/固件协作人 | 实板版本和连接器、可用PWM/控制输出、供电与共地、显示/摄像连接和软限位 | 接线表、固件自检与真机负载/噪声/复位记录 |
| 采购协作人 | 盘点已有件；**主板已定 GOOUU ESP32-S3-CAM + 布局 A**；**必配 INMP441×2 / MAX98357 / TP4056**；E04/E05 跨轴排线属第二批，可先用通用长线过渡；正式壳体等 CAD | SKU、价格与订单状态；到货尺寸回填 `parameters.json` |
| 音频协作人 | 固定底座双麦声学通道、前向扬声器声腔、转动噪声和 AEC | 原始实测记录，不因模型有孔/有密封材料就判通过；**若换板，AEC 必须重测，不得套用 Korvo 结论**；初赛不阻塞，决赛前必须完成 |
| 展示/视觉协作人 | 用当前主视觉；建模审阅图标明占位阶段，AI图标明概念 | 与BOM/尺寸一致的展板说明；正式爆炸图等结构接口确定后制作 |

## 历史与新旧入口

- [10月9日用户原始分享清单](archive/procurement/2026-10-09-original-shared-list.md)：原文副本，未改动来源。
- [10月5日通用采购清单](archive/procurement/2026-10-05-hardware-purchase-list.md)：历史规划。
- [席位牌v1](archive/seat-card-v1/README.md)、[旧外壳说明](archive/legacy-enclosure/EffMeet2_外壳说明_v2.md)：不作为当前外观规格。
- docs/handoff/2026-10-10-robot-design-and-bom.md只作导航；本文件是此次交接正文。
- 同步目录前已快进合并远端d052490（SQLite与台架修复、参与端去重），本次不撤销或改写该提交。
