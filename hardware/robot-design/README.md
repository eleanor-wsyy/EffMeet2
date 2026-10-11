# EffMeet2 · 机器人设计与采购统一入口

**当前：NOMI方向／GOOUU核心板／布局A／灰黑PLA Matte，v4工程候选。** 电脑伴侣路线A不变。当前模型已改，不再是仅AI效果图。

## 从这里开始

| 内容 | 当前入口 |
|---|---|
| 本次改动与接手顺序 | [HANDOFF](HANDOFF.md) |
| 可编辑模型、10张实渲、3张说明图纸 | [NOMI布局A-v4](round-yaw-v2/revision-20261011-nomi-layoutA/README.md) |
| 唯一几何／位置参数 | [parameters.json](round-yaw-v2/parameters.json) |
| 唯一当前采购明细 | [BOM第12节](round-yaw-v2/BOM.md#final-purchase-decision) |
| 安装顺序 | [ASSEMBLY_GUIDE](round-yaw-v2/ASSEMBLY_GUIDE.md) |
| 少操作打印与放行条件 | [PRINT_PLAN](round-yaw-v2/PRINT_PLAN.md) |
| 功能与实机验收 | [TEST_GUIDE](round-yaw-v2/TEST_GUIDE.md)／[空白记录模板](round-yaw-v2/TEST_RECORD_TEMPLATE.csv) |
| 已实现／未锁定工程接口 | [ENGINEERING_REVIEW](round-yaw-v2/revision-20261011-nomi-layoutA/ENGINEERING_REVIEW.md) |
| 机器可读入口 | [manifest.json](manifest.json) |

套装已含屏和OV3660，不重复采购；新增外置INMP441×2／MAX98357A／TP4056必须纳入底座。扩展板未实测，不宣称完整套装都能装入。

## 本轮到底改了什么

圆润连续头壳、Ø106圆打印脸、真实矩形屏窗、圆润遮盖、头底接收面／法兰／D接收、短颈和双轴承／传动预留、新板／电池封装、固定INMP441声孔、四条声槽、后供电／通风、按钮和状态窗；安装、采购、打印和测试同版同步。

模型保持原生Screw／Boolean／Lattice／Solidify，所有头部控制同轴旋转。渲染图来自实际模型，不是AI想象内部结构；旧v2文件和原始视觉图保留。

## 验证边界

阶段仍为reversible_blockout，final_design_approved=false、manufacturing_ready=false、hardware_validated=false。

五个外壳／颈部件的闭合与连通、十五个名义预留盒、三姿态壳体依赖／14mm间隙已检查。真实FPC、全件固定／工具空间、带轮齿形／舵盘、滑盖导向、正式料公差和固件／实机性能未放行，不能把渲染图和闭合网格当成验收PASS。

## 历史和复建

- [旧v2与历史材料索引](round-yaw-v2/README.md)；[archive](archive/README.md)。
- [旧STL警示](round-yaw-v2/stl/README.md)：不是当前打印包，不能直接整机打印。
- v4生成源位于当前v4目录；复建用新的审阅ID，禁止覆盖冻结图。
- [离线验收脚本](verify_delivery.py)检查路径／当前参数／几何证据／26项NOT_RUN／散列，不冒充实机测试。
- [本地ZIP打包](round-yaw-v2/package_delivery.py)仅生成忽略目录中的归档，Git提交单一源文件和图纸，不重复提交ZIP。
