# hardware/electronics — 供电与接线

硬件采购表不在这里重复维护，当前唯一BOM为[机器人设计目录的BOM](../robot-design/round-yaw-v2/BOM.md)。外观、可编辑模型、尺寸预留及交接见[统一入口](../robot-design/README.md)与[HANDOFF](../robot-design/HANDOFF.md)。

## 接线基线

台架接线表（与固件 `app_config.h` 对齐，2026-10-21）：[wiring-bench.md](wiring-bench.md)。
含电源轨分配（舵机独立 5V、共地）、INMP441/MAX98357A/舵机/状态灯引脚表、
已占用 GPIO 汇总、台架 REPL 验证命令。

## 本目录职责

后续记录真实板卡版本、连接器/针脚、供电与共地、PWM信号引出、接线图、峰值电流及到货/实机验证。实际接线和控制方案未冻结；不要把BOM或模型姿态当作接线/固件已经完成。

本次只更新资料入口，未新增接线图或驱动实现。
