# 归档 · 微雪 ESP32-S3-CAM-OV3660 评估（2026-10-12）

> **未采用。** 当前主板是 **GOOUU ESP32-S3-CAM**，见 [`../../round-yaw-v2/GOOUU-BOARD-SPEC.md`](../../round-yaw-v2/GOOUU-BOARD-SPEC.md)。
> 本目录保留评估过程与规格，供日后若微雪国内现货到位时重新评估。

## 为什么没选它

| 维度 | 微雪 ESP32-S3-CAM-OV3660 | GOOUU ESP32-S3-CAM（采用） |
|---|---|---|
| **音频** | ✅ **板载双麦阵列 + ES8311/ES7210 + NS4150B 功放** | ❌ 无，须外接 INMP441×2 + MAX98357 |
| 电池 | ✅ 板载 3.7V 充放（ETA6098） | ❌ 无，须外接 TP4056 |
| 相机 | ✅ 板载 OV3660（2048×1536、硬件 JPEG） | ✅ 带 OV3660（FPC 外接） |
| 屏接口 | ✅ 18PIN SPI/QSPI 专用座，官方驱动内建 | ⚠️ 走排针 |
| 国内到货 | ❌ **要等**（官方店海外链路；淘宝官方店未确认现货） | ✅ **次日达** |
| 板体尺寸 | ❌ 未公布（文档站 Dimensions 节空白） | ✅ **62.6×28.3mm** |
| 价格 | US$16.99–19.99 / ≈¥120–150 | **¥7 起** |

**决定性理由：交付速度。** 10.21 截止，微雪国内拿货赶不上；GOOUU 次日达，且板体尺寸已知，能立刻开工建模。

**代价（如实记录）**：GOOUU 无板载音频，AEC 失去硬件回声参考通路，只能软件兜底——这是换板付出的主要技术代价。

## 本目录内容

| 文件 | 内容 |
|---|---|
| `WAVESHARE-BOARD-SPEC.md` | 微雪板完整规格：**从官方 BSP 源码**取到的全 GPIO 表（I2C/I2S 双麦+功放/LCD SPI/24PIN DVP/SD/按键/电池）、屏选型（2.0″/2.8″/3.5″/1.83″）、OV3660 参数、原理图 PDF 与源码链接 |

## 若日后重新评估

- 微雪官方文档站：https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx
- BSP 源码（引脚真源）：https://github.com/waveshareteam/ESP32-S3-CAM-OVxxxx
- 原理图 Rev1.1：https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf

**切换回微雪需要改的**：BOM §12.1 声明、§12.2 E01/E02/E04/E05/E11、§12.0 状态表、删 E14/E15/E16、HANDOFF 决策节、MODELING_BRIEF §3.1 音频与跨轴两行、ASSEMBLY_GUIDE 对照表。
