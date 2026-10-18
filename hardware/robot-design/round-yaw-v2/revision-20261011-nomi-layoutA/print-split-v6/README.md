# v6 紧凑候选 · 布局A2（2026-10-13，当前第一入口）

**v6 = 布局A2：核心板＋摄像头＋屏进头部；麦／功放／扬声器／舵机／停止键固定在底座，麦不随头转。**
原因：摄像头 FPC 实测仅 14mm，禁止裁剪或加长，无法从底座跨轴到头部；因此板必须与摄像头同在头内。
跨轴只剩约 9 根细软线（5V、GND、3V3?、I2S BCLK、WS、MIC SD、AMP DIN、SERVO PWM、KEY），穿空心轴 Ø22 孔（Ø10 禁入区，两端各一线夹）。

## 文件

| 内容 | 文件 |
|---|---|
| 模型（场景 `N6_COMPACT_CANDIDATE`） | [EffMeet2_NOMI_布局A_v6_紧凑候选.blend](EffMeet2_NOMI_布局A_v6_紧凑候选.blend) |
| 生成源（尺寸全在 `PARAMS`） | [build_v6.py](build_v6.py) |
| 件表 | [parts.json](parts.json) / [PARTS.csv](PARTS.csv)（31 件） |
| 候选 STL | `candidate-stl/Pxx_*_UNVERIFIED.stl` |
| 检查 | [production/stage1-checks.json](production/stage1-checks.json)、[production/export-byte-audit.json](production/export-byte-audit.json)、[production/decimate-audit.json](production/decimate-audit.json)（减面自校验）、[production/plate-registry.json](production/plate-registry.json)（盘内容+层数指纹） |
| 实测表 / 打印手册 | [MEASUREMENTS.csv](MEASUREMENTS.csv) / [PLATE-RUNBOOK.md](PLATE-RUNBOOK.md) |
| **待测清单（2026-10-15）** | [MEASURE-TODO.md](MEASURE-TODO.md) —— 全量缺测数据，A组中午可测（LCD四孔等） |
| **打印教训集（2026-10-15/18）** | [PRINT-LESSONS.md](PRINT-LESSONS.md) —— 排机/耗材/预设/炒面/样片纪律 **47 条**。**37–47 是 10-18 实打成功配方**（P03 翻/P05P06 不翻/P06 阻挡器/P26 FPC 孔/P24P25 版本/P02 接缝/P20 立柱/P28 brim/配合台账/60 秒自检）。**教训22/26/30 均带实测更正**（墙层数不致丢层、减面须数三角面、P20 几何无罪），**教训34–36 是 10-17 读实存预设后的铁证**（0.20 H2S 预设 wall_loops=6+sbpo=0 从未重存／薄壁须用内外双墙宽／Bambu CLI 能 `--info` 不能 `--slice`）。原文保留+更正并列，勿只读原文 |
| **切片设置卡（2026-10-16）** | [SLICE-CARD.md](SLICE-CARD.md) —— 小件缺特征/圆孔打不出来时照着点的一页：第0步工程核对（层数指纹）→支撑范围→检查薄壁→挤出/耗材，含重打前最小验证流程 |
| **无源件专账（2026-10-16）** | [UNREGISTERED-PARTS.md](UNREGISTERED-PARTS.md) —— P32/P18T 只存在于 3MF 内部、无建模源不可复现；含 P04「假减面」实测证据。**不进 PARTS.csv**（会被 finalize_exports.py 重写冲掉） |
| **审计工具（2026-10-16）** | [tools/thinwall_audit.py](tools/thinwall_audit.py) 逐层薄壁/空层审计（补既有三关的盲区）；[tools/plate_registry.py](tools/plate_registry.py) 盘内容+层数指纹登记；[tools/decimate_planar.py](tools/decimate_planar.py) 减面（已加三角面自校验，拒绝 no-op 产物） |
| **安装手册 v4（2026-10-18）** | [ASSEMBLY.md](ASSEMBLY.md) —— **顺序：线 → P02 → P14 → 头 → 最后 P24**；P24 无面板螺钉、P05/P06 一组 4×M3×55–60、P13 在 P03 下方 D 平面、P03/P04 M2 顶丝、P20 有件也要胶；含 §0.6 P02/P20 应急、§7 螺钉表、§8 版本陷阱、§9 时间盒 |
| **新手测量指南（2026-10-15）** | [MEASURE-GUIDE.md](MEASURE-GUIDE.md) —— 卡尺教学+15张图文测量卡+记录表，交新手执行到货测量；图文PDF在outputs |
| 盘文件（每盘一个 3MF＋俯视预览） | [plates/](plates/)（[排布记录](plates/plates.json)，256 起点排布，未切片） |
| **可打印盘（2026-10-16 最新）** | [plates-merged/](plates-merged/) —— 已打：SAFE/THINP25/G1/G2NIGHT/B1p-v2/NIGHT/BNIGHT2(停,湿黑料)/COUPON；待打：**G3p-DEC**(P02减面13614,已验证)/INTERN2-DEC(P04+P20/P18T/P32×2)/BVIS或BVIS-TILT(黑P14+P28,烘料后)/NECK-PETG-A1(PETG替身颈+滑片)/S1PETG-A1(可选备份)；减面STL在 `decimated/`；作废盘归档 `_superseded/`。**每盘的件数/层高/隐含层数/无源件见 [PLATE-RUNBOOK §6 盘登记总表](PLATE-RUNBOOK.md)**（由 `tools/plate_registry.py` 实测生成）。⚠️ INTERN2-DEC 里的 `P04_DRIVER32T_dec` 名带 dec 实为**未减面** 4896 面（见 UNREGISTERED-PARTS.md） |
| **重打盘（2026-10-18）** | [reprint-20261018/](../../../../../reprint-20261018/) —— **P03 翻转 + P05/P06 原向 + P28 独立盘**；**已实打成功**。设置卡 [PRINT-CARD-REPRINT.md](../../../../../reprint-20261018/PRINT-CARD-REPRINT.md)：P03 翻、P05/P06 不翻、P06 Ø34×1.0 阻挡器、P28 10mm brim |
| **P15/P17/P26/P29 修复盘（2026-10-19）** | [TMP-FIX-P15P17P26P29_BLACK_016.3mf](plates-merged/TMP-FIX-P15P17P26P29_BLACK_016.3mf) + [盘卡](plates-merged/PLATE-CARD-P15P17P26P29.md) —— **P26 已转 90°（镜管朝床）**；P15/P17 **局部树支撑 5%**（P15 z15–16/20–21；P17 z7–8 托盘外沿）；P29 仅 brim5/支撑关；**P24 摄像孔另钻 6.8**；盘卡含返工原因/P24 补改 |
| 渲染 | [00 v5/v6 对比](renders/00_compare_v5_v6.png)、[01 主视](renders/01_hero.png)、[02 正视](renders/02_front.png)、[03 侧视](renders/03_side.png)、[05 内部](renders/05_internal.png) |

## 尺寸（mm，名义）

| | v5 | v6 |
|---|---|---|
| 整机 | 180×164×222 | **153×139.4×200.8** |
| 底座 | 180×164，盖顶 78 | **153×139.4，盖顶 66.3**（v4 剖面×0.85，壁/底 2.4） |
| 头 | ≈150×128×144 | **132 宽，y −47…+63，z 80.3…200.8**（球半径 66，半高 64；前缘 r57、Ø106 面板保留） |

头底距盖顶 14mm。头内：LCD 堆叠到 y −35.4；核心板竖装 PCB y −26、z 113.6…176.2，FPC/USB-C 端朝上，上方留 10mm USB-C 调试空间；LCD 排针侧留 12mm 杜邦净空。摄像头中心 z 173.2（窗口上沿＋17），FPC 直线跨距 9.55，余量 4.45；镜头孔与隐私滑盖同轴。

## 传动 2:1

MG90S → 32T（节径 20.37）→ 64T（节径 40.74，套空心轴 Ø29.8/22）。**GT2 188mm 闭环带，6mm 宽，C=44.84**（158/160/180 的 C 太短，200 偏远）；舵机 ±2mm 张紧槽。舵机 ±90° → 头 ±45°；软限 45°、硬限接触 48°（舵机 96°）。两只 6806 中心 z 36.5 / 56.5。

## 电源

不装扩展板（实测 95×87×12 放不下）、不装电池、不装 TP4056（推迟到路线B/决赛）。Demo 外供 5V≥2A，经后部 USB-C 输入小板（预算 20×15×6，**具体件未选**）。

## 检查结果（2026-10-13）

- 外壳评估网格：头/面板/颈/杯/盖 非流形 0、边界边 0、均 1 个连通块；体积 101 981 / 13 864 / 18 359 / 91 359 / 34 435 mm³。
- 31 件打印件两两重叠 0；打印件与 18 个元件代理重叠 0（BVH，表面内缩 0.05mm，贴面不计）。
- 代理全部在外壳内；yaw −45/0/+45 旋转组与固定组重叠均 0。
- STL 字节复读：31/31 闭合、正体积；全部放得下 256 盘（灰：头壳 132×120.5×110、杯 153×139.4×54.1、盖 145.7×132.7×9.9）。

## 接口处理（2026-10-15）

- 当前采购执行口径已在唯一[BOM §12](../../BOM.md#final-purchase-decision)统一到v6/A2：电池/TP4056/摄像跨轴FPC为0，新增E17输入板待选，打印件31件，旧v5长螺钉数量不沿用。
- [INTERFACE_GATES.md](INTERFACE_GATES.md)给出面板/LCD/FPC/输入板/传动/动态线束/脚垫逐项证据与放行门槛。
- [面板三点固定R1](review-20261015/face-retention-r1/)为独立候选，未修改当前canonical模型、源或31个STL；通过实物样片后才能合并。
- 杯底z=2mm与BOM C07约2mm硅胶脚垫预留一致；200.8是含0基准的名义包络，裸几何底到顶约198.77mm，脚垫未实测/未安装。

## 未验证（UNVERIFIED）

LCD 四孔位（按 80×45 假定）及玻璃到 PCB 深度（假定 4mm）；麦/功放/扬声器/舵机/轴承/GT2 带尚未到货，按采购页尺寸；USB-C 输入板未选型；跨轴细线弯折寿命；GT2 齿形为圆弧槽假设，未认证；舵机输出轴偏移。

## 生成顺序

1. `blender -b ../../EffMeet2_圆润转头版_封装布局_v2.blend --python build_v6.py`（重建 blend、检查、渲染；`EFFMEET_SKIP_RENDER=1` 可跳过渲染）
2. `blender -b EffMeet2_NOMI_布局A_v6_紧凑候选.blend --python extract_export_meshes.py`
3. `python finalize_exports.py`（manifold3d 取自 `local-only/mesh-tools`）
4. `python verify_v6_delivery.py`

## 状态

stage = reversible_blockout；final_design_approved / manufacturing_ready / hardware_validated = **false**；26 项硬件测试仍 **NOT_RUN**；全部件 slicer/sample_print = NOT_RUN，release = CANDIDATE_NOT_RELEASED。代理与 KEEP_OUT 不导出。
