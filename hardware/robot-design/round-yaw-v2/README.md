> **2026-10-13 起当前为 [v6 紧凑候选·布局A2](revision-20261011-nomi-layoutA/print-split-v6/README.md)，优先于 v5/v4；v5 亦为历史。** 现行安装顺序 = print-split-v6/ASSEMBLY.md（附图解版）；打印执行 = PLATE-RUNBOOK。
>
> 以下 v4 内容仅作历史与追溯：旧"布局A=板在底座"、Ø106 圆脸、1:1 传动均作废，不得作为当前接口/尺寸依据。

# 圆润转头方案 · 当前模型与资料索引

**当前模型是 v6 紧凑候选（布局A2）**，见 [print-split-v6](revision-20261011-nomi-layoutA/print-split-v6/README.md)；v4/v5 与旧 Korvo-v2 均仅作历史。

- [当前入口 v6（模型/状态图/打印/安装）](revision-20261011-nomi-layoutA/print-split-v6/README.md)
- [唯一几何参数源](parameters.json)
- [唯一采购清单第12节](BOM.md#final-purchase-decision)
- [现行安装手册](revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md)（图解版同目录）／[打印执行](revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md)／[测试指南](TEST_GUIDE.md)／[记录模板](TEST_RECORD_TEMPLATE.csv)
- [外观／安装接口同步](EXTERIOR_ASSEMBLY_REVISION.md)／[建模任务书](MODELING_BRIEF.md)
- [统一HANDOFF](../HANDOFF.md)

阶段仍为reversible_blockout，manufacturing_ready=false、hardware_validated=false。v4已做外观与部分接收接口及名义封装检查；实物尺寸、FPC寿命、完整支架／夹持／传动仍需验证。

## 保留的历史材料

- [旧v2模型](EffMeet2_圆润转头版_封装布局_v2.blend)和[renders/review-02](renders/review-02/01_assembled.png)：旧Korvo占位记录，不用于证明新GOOUU方案可装配。
- [旧6项fit-report](fit-report.json)与[旧网格报告](production/validation_report.json)：只属于旧模型。
- [NOMI方向AI参考](concept/nomi-aligned-20261010/EffMeet2_NOMI方向_现有硬件_效果图.png)：审美来源，不是现行CAD／打印件照片。
- **可上机样片**：[fit-coupons](fit-coupons/README.md)。旧打印 STL 已于 2026-10-12 删除；`build_print_parts.py` 保留为历史源，不能代替 v4。
- [1:1配合样片](fit-coupons/README.md)：现有实验输入，正式料、真实零件和具体配合仍要重测。

当前ZIP应包含v4模型／图纸／参数和同版指南；ZIP本地生成，不入Git，不把旧包当最新版。
