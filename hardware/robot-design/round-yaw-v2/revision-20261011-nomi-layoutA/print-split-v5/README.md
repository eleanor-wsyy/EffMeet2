# 在议 · NOMI布局A · v5拆件候选

**本轮按SPLIT_PLAN v1.1执行：已有外观件清理、补真实机构/支架、逐件候选打印交付。不是制造放行。** 所有实测接口unverified；原生修改器/旧场景保留；manifest状态字段不改。

## 给下一位AI的入口

1. [PARTS.md](PARTS.md)：实际件名/数量/色/朝向起点/支撑/所属盘，CSV可回填。
2. **[PLATE-RUNBOOK.md](PLATE-RUNBOOK.md)：盘 × 机器 × 特殊设置执行口径**——每盘推荐机型、每盘特殊设置（Brim/层高/朝向/支撑）、全局切片设置、当前打印状态。**上机前先读这份。**
3. [ASSEMBLY.md](ASSEMBLY.md)：按真实分件和接收接口装配；轴承螺钉不可与夹紧螺钉相交。
4. [PRINTING.md](PRINTING.md)：PETG样片→正式PLA Matte复测→切片确认→灰壳。
5. [MEASUREMENTS.csv](MEASUREMENTS.csv)、[SLICER_CHECKLIST.csv](SLICER_CHECKLIST.csv)：未知尺寸、最终朝向/支撑保持空。
6. 唯一 [parameters.json](../../parameters.json)、[BOM§12](../../BOM.md#final-purchase-decision)、[TEST_GUIDE](../../TEST_GUIDE.md)。v4参数原样冻结在parameters-v4-frozen.json，不能用旧fit-report给新结构背书。

## 模型和独立文件

- 原生 [v5拆件候选.blend](EffMeet2_NOMI_布局A_v5_拆件候选.blend)，场景 `N5_PRINT_SPLIT_CANDIDATE`。保留 EFFMEET2_PACKAGING_V1 / R2_* / Scene / N4场景，保留Screw/Boolean/Lattice/Solidify及头部依赖。
- 每件独立候选STL在candidate-stl/，名称包含UNVERIFIED；具体清单只以parts.json为准，禁止将KEEP_OUT、电子占位、轴承/舵机/屏幕等代理、眼睛、灯、地面当打印件。
- [几何预排3MF目录](plate-start-layouts.json)：只含几何，不含打印机、材料配置、支撑或G-code，不叫“已切片”。盘数不冻结，不为凑7盘改件数。
- [预排图](plate-start-layouts.png)是包围尺寸示意；[件号索引](renders/06_parts_index.png)来自实际模型的评估网格，缩放只为阅读，不是工程比例图。
- [当前主视觉](renders/01_hero_candidate.png)、[内部结构](renders/05_internal_candidate.png)是真实Blender模型渲染，不是AI重画图。外观仍是圆头/Ø106圆黑脸/普通矩形LCD/短颈/固定圆润底座。

## 与v4的实质变化

- 双6806分体夹座、承力塔、4根隔柱、空心轴轴肩/局部D面/下夹环、可调舵机架、两只64齿候选轮。
- 隐私后导向/滑片/前压框三件分开；停止键带防脱底脚、导向托座；短颈止转舌与上盖固定限位形成候选硬限位。
- LCD两框、相机托架/压片、主板托架/压条、两麦托架与声管/压条、功放/充电/电池托盘、扬声器筒/前圈、两线束鞍均为真实独立结构。
- 电池预算旋转90度移至(53,0,14)；功放移至(20,-34.3,25)。只覆写v5布局，不悄悄更新v4旧报告。扩展板尺寸未测仍不纳入。
- 上盖螺钉接收柱贴合原生外轮廓，不靠渲染隐藏凸出。接收孔/螺母、轴承夹紧、舵盘、屏模组、开关行程均需样片。

## 证据与再生成

`production/mesh-audit.json`保留初始评估结果与导出修复记录。Manifold3D只清理导出副本，不改原生模型；`export-byte-audit.json`重读实际32位STL检查闭合、正体积。原始独立检查记录仍保留，不擦掉数值警告。

生成顺序：

1. Blender后台加载**输入v4.blend**，运行build_print_split.py（创建隔离v5场景，不能加载v5再重复运行）。
2. 加载新v5.blend运行extract_export_meshes.py，将原生评估网格写入ignored local-only/。
3. Python运行finalize_exports.py（numpy+manifold3d3.5.4），再运行make_print_delivery.py。Windows开发环境依赖放在ignored local-only/mesh-tools；不提交库缓存。
4. 加载v5.blend运行render_print_split.py；用finish_docs_and_boards.py补件号标签/图板/回填表；运行verify_print_delivery.py及目录根verify_delivery.py。
5. 所有硬件尺寸变更同时核对parameters及源内显式几何控制，并重建各证据。当前不是可任意改尺寸就自动重建全部关系的参数化机械CAD。

**未完成的实际验收：**真实切片/打印、实物尺寸/孔/头形、齿带和舵盘、轴肩/夹紧/强度、按键/遮挡、动态线束、音频/AEC、电源/温升/固件。26项模板保持NOT_RUN。`stage=reversible_blockout`，三个放行布尔值全部false。

### 原生姿态评估警告

三姿态头壳都保持14mm高度间距且闭合，但Boolean评估体积相对差约0.0132%，作为WARN保留；不声称原生姿态是已验证机械/固件rig。最终独立STL按中性装配态导出并独立核实，不使用姿态图替代实机验收。
