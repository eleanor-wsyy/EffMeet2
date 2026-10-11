# 来源：当前GOOUU方案与证据边界

- **采购和已下单套装**：[GOOUU-BOARD-SPEC](../GOOUU-BOARD-SPEC.md)，基线提交f0788c8。核心板62.6×28.3来自仓库商品尺寸图记录；扩展板、屏总尺寸、模块／接头仍待实物。订单记录由仓库提供，不是本轮验证物流。
- **屏**：套装HSD028309 A6／J2单排14针，SPI来自商品照片推断，并非已经核准的规格书。85×55PCB和73.06×50.54玻璃仅是当前安装预算，不是此屏制造数据；不另购微雪SKU27579。
- **外接芯片原理资料**：[MAX98357A官方资料](https://www.analog.com/en/products/max98357a.html)，[INMP441官方资料](https://invensense.tdk.com/products/digital/inmp441/)。芯片规格不能证明廉价模块PCB／接头尺寸、接线正确或系统AEC已完成。
- **已废弃板方案**：[微雪评估归档](../../archive/waveshare-board-eval-20261012/README.md)。其37×37、18PIN／24PIN与板载音频不再是当前依据。
- **造型**：[NOMI方向原图](../concept/nomi-aligned-20261010/EffMeet2_NOMI方向_现有硬件_效果图.png)和其[SOURCE](../concept/nomi-aligned-20261010/SOURCE.md)。仅参考圆头／圆脸／短连接，不复制品牌、机构、车载底座或性能。
- **建模**：Blender5.2.1LTS实际运行；对应[Boolean](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/booleans.html)、[Screw](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/screw.html)、[Lattice](https://docs.blender.org/manual/en/5.2/modeling/modifiers/deform/lattice.html)、[Solidify](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/solidify.html)。保留原生控制，检查评估网格，不强行把剖面边网当作闭合实体。

渲染全由实际模型生成；电子／座／轮是注明尺寸假设的代理，不把AI图、名义预算或芯片手册当实机／装配验收。
