> **v5拆件更新优先于下文v4历史细节。** 当前逐件模型/件表/接收界面见 [v5交付](revision-20261011-nomi-layoutA/print-split-v5/README.md)，安装顺序见其ASSEMBLY.md，朝向/支撑回填见PRINTING.md。实物验收及制造状态未放行。

# v4 · 外观与安装接口同步

更新：2026-10-11。**NOMI圆头＋圆黑脸的造型方向保留，工程基线改为GOOUU／布局A／灰黑PLA Matte。** 本轮已生成真实模型候选及实渲图，不能再用“仅AI效果图、CAD未改”描述。

- [当前模型和图纸](revision-20261011-nomi-layoutA/README.md)
- [完整工程复核和未验证接口](revision-20261011-nomi-layoutA/ENGINEERING_REVIEW.md)
- [更新后的安装指南](ASSEMBLY_GUIDE.md)
- [低工序打印方案](PRINT_PLAN.md)
- [唯一采购清单第12节](BOM.md#final-purchase-decision)

## 已同步到模型

Ø106圆打印面板、58.2×43.8真实矩形屏窗和背面让位、圆脸上部镜头／圆润遮盖、头壳3.2底接收面／隐藏法兰／两处M3候选孔、短颈阶梯D接收和Ø22线通道、双6806分置预留、1:1传动预留、固定后部GOOUU主板、双INMP441／MAX98357A／TP4056预留及右下电池、四条前声槽、固定麦孔、后USB线口／通风及前肩按钮。

尺寸／位置维护在parameters.json；新模型独立保留原Screw／Boolean／Lattice／Solidify控制及头部姿态依赖，不覆盖旧v2模型。

## 不因造型删除的功能

固定双INMP441不跟着头转；只有显示线束和相机排线跨轴；真实间隙14mm、±45°目标不变；隐私仍物理遮盖；停止键仍只停止播报，不当电机急停；状态灯需真实事件驱动；底座保留电子容量、出声和通风，不压成车载薄垫。

## 未放行项

轴承夹持与底座承力固定、轴肩／防松、GT2齿形／舵盘、电子件独立支架、滑盖导向／防脱、真实FPC定义／弯折半径／50循环、打印公差和固件／实机验收仍待完成。新模型渲染不是这些项的测试PASS，manufacturing_ready／hardware_validated仍为false。
