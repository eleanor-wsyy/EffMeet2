> **⛔ 历史决策记录（v4，2026-10-11）。装配操作只认 [print-split-v6/ASSEMBLY.md](revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md)（附图解版，2026-10-21 修订）。**
>
> **v5/v4 均已冻结为历史；当前是 v6 布局A2（板/屏/摄像头在头部）。** 本文所述 Ø106 圆脸、1:1 传动、板在底座、TP4056/电池预留等均已作废，不得作为当前接口依据。

# v4 · 外观与安装接口同步

更新：2026-10-11（历史）。**NOMI圆头＋圆黑脸方向保留；工程基线已从本文的"布局 A／板在底座"演进到 v6 布局A2。**

- [v4 模型和图纸（历史）](revision-20261011-nomi-layoutA/README.md)
- [v4 工程复核（历史）](revision-20261011-nomi-layoutA/ENGINEERING_REVIEW.md)
- [现行安装手册](revision-20261011-nomi-layoutA/print-split-v6/ASSEMBLY.md)
- [现行打印执行](revision-20261011-nomi-layoutA/print-split-v6/PLATE-RUNBOOK.md)
- [唯一采购清单第12节](BOM.md#final-purchase-decision)

## 已同步到模型

Ø106圆打印面板、58.2×43.8真实矩形屏窗和背面让位、圆脸上部镜头／圆润遮盖、头壳3.2底接收面／隐藏法兰／两处M3候选孔、短颈阶梯D接收和Ø22线通道、双6806分置预留、1:1传动预留、固定后部GOOUU主板、双INMP441／MAX98357A／TP4056预留及右下电池、四条前声槽、固定麦孔、后USB线口／通风及前肩按钮。

尺寸／位置维护在parameters.json；新模型独立保留原Screw／Boolean／Lattice／Solidify控制及头部姿态依赖，不覆盖旧v2模型。

## 不因造型删除的功能

固定双INMP441不跟着头转；只有显示线束和相机排线跨轴；真实间隙14mm、±45°目标不变；隐私仍物理遮盖；停止键仍只停止播报，不当电机急停；状态灯需真实事件驱动；底座保留电子容量、出声和通风，不压成车载薄垫。

## 未放行项

轴承夹持与底座承力固定、轴肩／防松、GT2齿形／舵盘、电子件独立支架、滑盖导向／防脱、真实FPC定义／弯折半径／50循环、打印公差和固件／实机验收仍待完成。新模型渲染不是这些项的测试PASS，manufacturing_ready／hardware_validated仍为false。
