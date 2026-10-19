> **当前入口（2026-10-13）：[v6紧凑候选·布局A2](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/README.md)。** 153×139.4×200.8，核心板＋摄像头＋屏进头，麦/功放/扬声器/舵机固定底座；31件候选，未切片、未制造放行。v5（G1/G2已停打作废）及v4保留为历史。
>
> 历史：[NOMI布局A v5](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/README.md)，41件独立候选。

# EffMeet2 · 机器人设计与采购统一入口

**当前：NOMI方向／GOOUU核心板／布局A／灰黑PLA Matte，v4工程候选。** 电脑伴侣路线A不变。当前模型已改，不再是仅AI效果图。

## 从这里开始

| 内容 | 当前入口 |
|---|---|
| **接手第一入口：当前状态与下一步** | [**HANDOFF**](HANDOFF.md)（顶部「2026-10-12 会话收尾」节） |
| 可编辑模型、10张实渲、3张说明图纸 | [NOMI布局A-v4](round-yaw-v2/revision-20261011-nomi-layoutA/README.md) |
| **打印件拆分任务书（交接管方执行）** | [**SPLIT_PLAN**](round-yaw-v2/revision-20261011-nomi-layoutA/SPLIT_PLAN.md) |
| **打印执行：盘×机器×特殊设置** | [**v6 PLATE-RUNBOOK**](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md)（v5 [旧手册](round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v5/PLATE-RUNBOOK.md)；G1/G2已停打作废） |
| 唯一几何／位置参数 | [parameters.json](round-yaw-v2/parameters.json) |
| 唯一当前采购明细 | [BOM第12节](round-yaw-v2/BOM.md#final-purchase-decision) |
| 安装顺序 | [ASSEMBLY_GUIDE](round-yaw-v2/ASSEMBLY_GUIDE.md) |
| 少操作打印与放行条件 | [PRINT_PLAN](round-yaw-v2/PRINT_PLAN.md) |
| 功能与实机验收 | [TEST_GUIDE](round-yaw-v2/TEST_GUIDE.md)／[空白记录模板](round-yaw-v2/TEST_RECORD_TEMPLATE.csv) |
| 已实现／未锁定工程接口 | [ENGINEERING_REVIEW](round-yaw-v2/revision-20261011-nomi-layoutA/ENGINEERING_REVIEW.md) |
| 机器可读入口 | [manifest.json](manifest.json) |

套装已含屏和OV3660，不重复采购；新增外置INMP441×2／MAX98357A／TP4056必须纳入底座。扩展板未实测，不宣称完整套装都能装入。

**采购状态**（执行表见 [BOM §12.0](round-yaw-v2/BOM.md#final-purchase-decision)）：✅ 已下单——GOOUU 套装（¥86.5）；PLA Matte 灰×2（**已到货**）、黑×1（**已下单未到货，勿重复下单**）。🔴 待下单——INMP441×2、MAX98357、TP4056（必买）；扬声器、6806×2、MG90S、五金线材（要买）。🟡 先翻库存——Type-C 线×2、5V 电源、舵机稳压、轻触开关。🟡 第二批——E04/E05 跨轴线束、GT2 带、3.7V 锂电。

**打印工作室**：学校 = 广美实验教学中心模型实验室（P2S×8 + H2S×10 + H2D×10 = 28 台，⚠️ **通风禁 ABS/ASA**，0.4 喷嘴＝**硬化钢**，需预约）；自有 = A1（256³）。分工：A1 打样片与黑料小件，学校打三件灰料大壳。**进度：G1 头壳（H2S）、G2 杯体（H2D）已上机（2026-10-12）；其余盘见 PLATE-RUNBOOK。**

## 本轮到底改了什么

圆润连续头壳、大平脸圆角矩形打印脸（106×96 R21，2026-10-19 FACEFLAT 取代 Ø106 圆脸）、真实矩形屏窗、圆润遮盖、头底接收面／法兰／D接收、短颈和双轴承／传动预留、新板／电池封装、固定INMP441声孔、四条声槽、后供电／通风、按钮和状态窗；安装、采购、打印和测试同版同步。

模型保持原生Screw／Boolean／Lattice／Solidify，所有头部控制同轴旋转。渲染图来自实际模型，不是AI想象内部结构；旧v2文件和原始视觉图保留。

## 验证边界

阶段仍为reversible_blockout，final_design_approved=false、manufacturing_ready=false、hardware_validated=false。

五个外壳／颈部件的闭合与连通、十五个名义预留盒、三姿态壳体依赖／14mm间隙已检查。真实FPC、全件固定／工具空间、带轮齿形／舵盘、滑盖导向、正式料公差和固件／实机性能未放行，不能把渲染图和闭合网格当成验收PASS。

## 历史和复建

- [旧v2与历史材料索引](round-yaw-v2/README.md)；[archive](archive/README.md)。
- **可上机样片**：[fit-coupons](round-yaw-v2/fit-coupons/README.md)（外观样片 + 4 件公差阶梯，优先用 PLA Matte 打）；旧 stl/ 草案已于 2026-10-12 删除。
- v4生成源位于当前v4目录；复建用新的审阅ID，禁止覆盖冻结图。
- [离线验收脚本](verify_delivery.py)检查路径／当前参数／几何证据／26项NOT_RUN／散列，不冒充实机测试。
- [本地ZIP打包](round-yaw-v2/package_delivery.py)仅生成忽略目录中的归档，Git提交单一源文件和图纸，不重复提交ZIP。
