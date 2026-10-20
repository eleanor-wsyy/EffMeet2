# 无仓内建模源的打印件专账（P32 / P18T）

> 2026-10-16 建立。**本文件是专账，不进 [PARTS.csv](PARTS.csv)** —— 因为
> [finalize_exports.py](finalize_exports.py) 每次运行都会**重写** PARTS.csv 与 parts.json，
> 手工加进去的行会被冲掉（PRINT-LESSONS 教训33）。
>
> 数据全部由 `tools/plate_registry.py` 从 3MF 内嵌几何实测读出，不是从文档抄的。
> 状态纪律：这些件**无源、不可复现、不可参数化修改**；`CANDIDATE_NOT_RELEASED`，
> 三个放行布尔保持 false。

## 为什么单独立账

`build_v6.py` 生成 32 件（P01–P31＋v6r3 新增 P33 摄像头背板；P32 编号特意跳过、保留给本账的麦胶座），存进 v6 blend 的 `N6_COMPACT_CANDIDATE` 场景，
再由 `extract_export_meshes.py` → `finalize_exports.py` 导出 `candidate-stl/` 并写 PARTS.csv。
**P32 与 P18T 完全不在这条链上**（P33 相反：从第一天起就在链上，正是吸取教训 33 的做法）：

| 检查项 | P32 | P18T |
|---|---|---|
| 在 `build_v6.py` 里 | ❌ 无 | ❌ 无 |
| 在 v6 blend（374 个对象）里 | ❌ 无匹配 | ❌ 无匹配 |
| 在 `candidate-stl/` 里 | ❌ 无 STL | ❌ 无 STL |
| 在 `PARTS.csv`（32 件）里 | ❌ 无 | ❌ 无 |
| 只存在于 | 3MF 盘内部 | 3MF 盘内部 |

后果：无法改参数重出、无法独立审计、无法追溯是谁按什么尺寸建的。
本次 P20 排查中若要动 P32 腔径，**根本无从下手**。

## P32 · INMP441 麦克风胶座（×2，左右）

来历：2026-10-16 学妹照片发现 INMP441 含两侧焊盘总宽 ≈17–18 > 板径 14，
P21/P22 压圈（ID≈14.6）与 P01 壁袋环（ID14.6）均装不进 → 作废 P21/P22、
P01 壁袋环弃用（P01 不返工），改新件 P32 胶座。设计意图见 [PLATE-RUNBOOK.md](PLATE-RUNBOOK.md) 末段：
腔 19×19×4.2 避焊盘、底 Ø6 声孔对 P01 壁 Ø2.4 声孔、四角压唇固模块、胶贴弯曲壁。

**实测（从 3MF 读出）**

| 盘 | 对象名 | 三角面 | 尺寸 mm |
|---|---|---|---|
| `TMP-MICHOLDER-GREY_020.3mf` | `P32_MIC_HOLDER_GLUE_L` / `_R` | 168 / 168 | 24.0 × 24.0 × 6.0 |
| `TMP-INTERN2-DEC_GREY_020.3mf` | `P32_HOLDER_L` / `_R` | 168 / 168 | 24.0 × 24.0 × 6.0 |

**命名漂移**：同一几何（168 面、24×24×6）在两盘里叫两个名字。

**可打印性**（`tools/thinwall_audit.py`，E=0.42 / lh=0.2）：
`k_max=8`、墙心残隙 3.58mm、thin_frac 未超标、空层 0 → **CLEAN / OK**。
> ⚠️ 更正：本日早些时候曾判 P32「最严重、0.0054mm² 数学零面积」，那是**带宽算法用错**
> （用了 `A/P` 而非薄片等周的 `2A/P`，且把"残隙≈0"误读成缺陷）。
> 残隙≈0 实际是**整数圈恰好填满**的理想态。P32 无需改腔径。

**待补**：建模源（脚本或 blend 对象）、腔径/声孔/压唇的实测核对、与 P01 壁 Ø2.4 声孔的对位验证。

## P18T · USB-C 5V 输入板容差托架

来历：P18 原托架按未选型 SKU 建模；SKU 未定 → 出"容差版" P18T 解除阻塞
（见 HANDOFF 10-15/10-16 节、[PLATE-RUNBOOK.md](PLATE-RUNBOOK.md):71 v6r3 容差窗口径）。

**实测（从 3MF 读出）—— 同一几何三个名字**

| 盘 | 对象名 | 三角面 | 尺寸 mm |
|---|---|---|---|
| `TMP-P18T_BLACK_020.3mf` | `P18_TOLERANT_CRADLE` | 224 | 32.0 × 24.0 × 14.4 |
| `TMP-BNIGHT2-BLACK_012.3mf` | `P18T_TOLERANT_CRADLE` | 224 | 32.0 × 24.0 × 14.4 |
| `TMP-INTERN2-DEC_GREY_020.3mf` | `P18T_CRADLE` | 224 | 32.0 × 24.0 × 14.4 |

**注意**：`TMP-P18T_BLACK_020` 里的对象名叫 `P18_TOLERANT_CRADLE`（无 T），
`tools/plate_registry.py` 的前缀匹配会把它误判成"P18 有源"。实际它与
`candidate-stl/P18_POWER_IN_TRAY_UNVERIFIED.stl`（**516 面**）是**不同网格**（224 面）。
→ 该工具的 `has_source` 只按名字前缀判断，**测不出同名不同网格**，这是已知局限。

**可打印性**：`k_max=3`、墙心残隙 0.188mm、空层 0 → **TIGHT / WARN**（可打印，非缺陷）。

**待补**：建模源、与 P18 的差异说明（容差窗口具体放大了多少）、命名统一。

## P04 · 名字里的 "dec" 是假的（附带发现）

不是无源件，但同属"盘内物件与仓库记录不符"：

| 盘 | 对象名 | 三角面 | 说明 |
|---|---|---|---|
| `TMP-INTERN2-DEC_GREY_020.3mf` | `P04_DRIVER32T_dec` | **4896** | 名字带 `dec`，实为**未减面** |
| `TMP-BNIGHT2-BLACK_012.3mf` | `P04_DRIVER32T_FLAT` | 4896 | 同上 |
| `plates-merged/decimated/P04_decimated.stl` | — | **4896** | 与 `candidate-stl/P04_DRIVER_32T_UNVERIFIED.stl` 逐面相同 |

原因见 PRINT-LESSONS **教训26 更正**：DECIMATE/DISSOLVE 只把共面三角形并成 n-gon
（4896→1266 个多边形），**STL 只存三角形**，重新三角化后仍是 4896。
HANDOFF 记的"P04 4896→1266"是拿三角面数比多边形数，量纲错误。
**机房老师反映的"网格过密"对 P04 从未解决。**

对照：P02 是**真减面**（STL 三角面 18134→13614，−24.93%，1.5°，dVol 0.0775%，dBbox 0），
入仓的 `decimated/P02_decimated.stl`(13614) 可复现、正确。

## 处置建议（按优先级）

1. **补建模源**：把 P32、P18T 写进 `build_v6.py`（或独立生成脚本），重跑
   `extract_export_meshes.py` → `finalize_exports.py`，让它们自动进 PARTS.csv 与 candidate-stl/。
   在补源之前，这两件**不应再被当成可迭代件**。
2. **统一命名**：一件一名，盘内对象名 = `Pxx_<NAME>`，与 PARTS.csv 的 id 对齐；
   禁止 `_dec`/`_FLAT`/`_BAKED` 这类描述处理状态的后缀与真实内容不符。
3. **P04 真要减面**：DISSOLVE 无效，改用能删内部顶点的方式（DECIMATE/COLLAPSE 或 remesh），
   并重新过教训26 阈值（|ΔV|<0.3% 且 bbox 逐位不变）。用
   `tools/decimate_planar.py` 跑，它现在会以**三角面数**判定并拒绝 no-op 产物。
