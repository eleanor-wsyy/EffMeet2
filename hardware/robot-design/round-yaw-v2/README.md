# 圆润转头方案 · 当前模型与资料索引

**当前模型是v4 NOMI／GOOUU布局A／灰黑PLA Matte候选**，不是旧Korvo-v2，也不是上轮AI效果图。

- [当前v4模型、主视觉、三视图和内舱／分解图](revision-20261011-nomi-layoutA/README.md)
- [唯一几何参数源](parameters.json)
- [唯一采购清单第12节](BOM.md#final-purchase-decision)
- [安装指南](ASSEMBLY_GUIDE.md)／[打印方案](PRINT_PLAN.md)／[测试指南](TEST_GUIDE.md)／[记录模板](TEST_RECORD_TEMPLATE.csv)
- [外观／安装接口同步](EXTERIOR_ASSEMBLY_REVISION.md)／[建模任务书](MODELING_BRIEF.md)
- [统一HANDOFF](../HANDOFF.md)

阶段仍为reversible_blockout，manufacturing_ready=false、hardware_validated=false。v4已做外观与部分接收接口及名义封装检查；实物尺寸、FPC寿命、完整支架／夹持／传动仍需验证。

## 保留的历史材料

- [旧v2模型](EffMeet2_圆润转头版_封装布局_v2.blend)和[renders/review-02](renders/review-02/01_assembled.png)：旧Korvo占位记录，不用于证明新GOOUU方案可装配。
- [旧6项fit-report](fit-report.json)与[旧网格报告](production/validation_report.json)：只属于旧模型。
- [NOMI方向AI参考](concept/nomi-aligned-20261010/EffMeet2_NOMI方向_现有硬件_效果图.png)：审美来源，不是现行CAD／打印件照片。
- [旧打印STL](stl/README.md)及build_print_parts.py：历史草案，尚未完成全件制造验证，不能直接拿来代替v4。
- [1:1配合样片](fit-coupons/README.md)：现有实验输入，正式料、真实零件和具体配合仍要重测。

当前ZIP应包含v4模型／图纸／参数和同版指南；ZIP本地生成，不入Git，不把旧包当最新版。
