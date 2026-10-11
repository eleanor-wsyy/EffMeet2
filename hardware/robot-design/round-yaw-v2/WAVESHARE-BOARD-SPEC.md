# 微雪 ESP32-S3-CAM-OV3660 · 官方硬件规格（建模依据）

> 来源：微雪官方 **板级支持包源码**（BSP 头文件）+ 官方文档站，2026-10-11 抓取。
> **这是目前最权威的口径**——客服与 wiki（"紧急编写中"）都给不出，但源码里是硬定义。
> 用途：给建模/接线/选屏/排线定尺寸与引脚。**板体外形尺寸仍缺**（见 §6）。

---

## 0. 一句话结论（对采购/建模的影响）

| 问题 | 答案 | 影响 |
|---|---|---|
| 18PIN 屏买哪款？ | **2.0″ 或 2.8″（320×240）**——官方驱动直接支持 | ✅ E02′ 可以下单 |
| 跨轴 FPC 多少线？ | LCD 是 **SPI 单线**（DATA0/PCLK/DC/CS），不是并口 | ✅ **E04 可以很细**，比原 Korvo 并口简单得多 |
| 摄像头是什么？ | **板载 24PIN DVP，8-bit**（D0–D7 + PCLK/VSYNC/HSYNC/XCLK） | E03 不再单购；镜头开孔坐标待实测 |
| 麦克风/喇叭？ | **板载双麦阵列 + 功放**，喇叭单元外接 | C06 麦孔按**实板麦位**开 |
| 停止键？ | **板载 BUTTON1 = GPIO15**，可直接引出 | E11 可简化为引出，不必另买按键模块 |
| 电池？ | 板载 **GH1.25 3.7V 充放**（ETA6098 管理），电压经 IO 扩展器 ADC | 底座需留电池仓 |
| 板体尺寸？ | **未公布**（文档站 Dimensions 节空白） | ⚠️ 建模前需实测或取卖家尺寸图 |

---

## 1. 板载能力（BSP_CAPS）

| 能力 | 有 | 说明 |
|---|---|---|
| DISPLAY | ✅ | 18PIN SPI/QSPI 屏接口 |
| TOUCH | ✅ | 触摸走 I2C + IO 扩展器 |
| BUTTONS | ✅ | 2 个 |
| AUDIO / SPEAKER / MIC | ✅ | 双麦阵列 + 功放 |
| LED | ✅ | USER 指示、充电指示 |
| SDCARD | ✅ | TF 卡槽 |
| CAMERA | ✅ | 24PIN DVP |
| IMU | ❌ | 无 |

**其他板载**：ESP32-S3R8（240MHz 双核）、8MB PSRAM、16MB Flash、陶瓷天线、Type-C、MP1605 电源、ETA6098 充电管理、**CH32V003F4U6 IO 扩展器**。

---

## 2. 完整引脚定义（官方 BSP `esp32_s3_cam_ovxxxx.h`）

### 2.1 I2C（IO 扩展器 + 触摸）
| 信号 | GPIO |
|---|---|
| I2C SCL | **7** |
| I2C SDA | **8** |

### 2.2 I2S 音频（双麦 + 功放）
| 信号 | GPIO | 说明 |
|---|---|---|
| I2S MCLK | **10** | |
| I2S SCLK | **11** | |
| I2S LCLK | **12** | |
| I2S DOUT | **14** | → 功放（NS4150B）→ 喇叭 |
| I2S DSIN | **13** | ← 双麦（ES7210） |
| POWER_AMP | NC | 功放使能由硬件控制 |

### 2.3 LCD（SPI/QSPI 18PIN）— **E04 跨轴排线就走这些**
| 信号 | GPIO | 说明 |
|---|---|---|
| LCD DATA0 | **1** | SPI 数据 |
| LCD DC | **3** | |
| LCD PCLK | **5** | SPI 时钟 |
| LCD CS | **6** | |
| LCD RST | **IO 扩展器 P1** | 非直出 GPIO |
| LCD BACKLIGHT | **IO 扩展器 PWM1** | 非直出 GPIO |
| TOUCH_RST | **IO 扩展器 P0** | |
| TOUCH_INT | **9** | |

> **对布局 A 的意义**：LCD 只需 **4 根信号 + 电源 + 触摸 2 根 + I2C 2 根**，跨轴 FPC 可以很细、弯折寿命风险远低于并口。

### 2.4 摄像头（24PIN DVP，8-bit）
| 信号 | GPIO | | 信号 | GPIO |
|---|---|---|---|---|
| CAM XCLK | **38** | | CAM D0 | **45** |
| CAM PCLK | **41** | | CAM D1 | **47** |
| CAM VSYNC | **17** | | CAM D2 | **48** |
| CAM HSYNC | **18** | | CAM D3 | **46** |
| | | | CAM D4 | **42** |
| | | | CAM D5 | **40** |
| | | | CAM D6 | **39** |
| | | | CAM D7 | **21** |

> 共 **12 根信号**（XCLK/PCLK/VSYNC/HSYNC + D0–D7）。

### 2.5 SD 卡
| 信号 | GPIO |
|---|---|
| SD D0 | **44** |
| SD CMD | **43** |
| SD CLK | **16** |

### 2.6 按键 / 电池 / LED
| 信号 | GPIO | 说明 |
|---|---|---|
| BUTTON0 | **0** | BOOT 键，可复用为自定义功能 |
| **BUTTON1** | **15** | **可直接引出作「停止播报」键**（E11） |
| BATTERY_VOLTAGE | **IO 扩展器 ADC** | 非直出 GPIO |
| USER LED | IO 扩展器 | |
| 充电指示 | 硬件 | |

---

## 3. 屏幕选型（E02′）——**官方驱动已内建**

| 配置宏 | 屏尺寸 | 分辨率 |
|---|---|---|
| `BSP_LCD_SIZE_2INCH` | **2.0″** | **320×240** |
| `BSP_LCD_SIZE_2_8INCH` | **2.8″** | **320×240** |
| `BSP_LCD_SIZE_3_5INCH` | 3.5″ | 320×480 |
| `BSP_LCD_SIZE_1_83INCH` | 1.83″ | 284×240 |

- **色彩**：RGB565、16bpp、大端
- **像素时钟**：80 MHz
- **接口**：SPI / QSPI（`SPI2_HOST`）

**推荐：2.8″（320×240）**——与「圆面板中央矩形窗」比例最协调（4:3 竖放 240×320），官方驱动零改动。若头部空间紧张则退 2.0″。

---

## 4. 摄像头参数（OV3660）

| 项 | 值 |
|---|---|
| 最大分辨率 | **2048×1536** |
| 接口 | DVP |
| 输出格式 | 8/10-bit Raw RGB、**JPEG 硬件压缩**、YUV/YCbCr422、RGB565 |
| 镜头 | **3.2mm** |
| 光圈 | F2.4 |
| 视场 | **D:68°** |

可选替代模组（同 24PIN DVP 接口）：OV5640（2592×1944，1/4″，4.1mm）、GC2145、GC0308。
**我们选 OV3660**：带硬件 JPEG，抓拍现场材料正好用。

---

## 5. 对 BOM / 建模的直接结论

| 项 | 变化 |
|---|---|
| **E02′** | **可下单**：2.8″ SPI 屏（或 2.0″），320×240，官方驱动支持 |
| **E04 LCD FPC** | **线数大减**：4 信号 + 触摸 2 + I2C 2 + 电源，可用细排线；寿命风险显著降低 |
| **E05 摄像 FPC** | 12 信号 + 电源；若板在底座、相机随头，需 12 线跨轴 |
| **E11 停止键** | **可简化**：直接引出板载 BUTTON1（GPIO15） |
| **E06 扬声器** | 仍需外接喇叭单元（板上有功放 NS4150B） |
| **C06 麦孔** | **必须按实板麦位开**，不得按概念图对称装饰开 |
| **布局 A 可行性** | ✅ 强化：LCD 线少，跨轴 FPC 由"高风险"降为"可控" |

---

## 6. 仍缺的（建模前必须补）

| 缺项 | 怎么拿 | 影响 |
|---|---|---|
| **板体外形尺寸** | ① 卖家/微雪索取尺寸图；② 到货卡尺实测；③ 原理图 PDF 上的机械层 | **头壳/底座腔体**无法定稿 |
| **镜头在板上的坐标** | 同上 | 面板摄像孔位置 |
| **Type-C 凸出量** | 实测 | 底座侧面凹槽 |
| **18PIN 接口物理规格**（间距/方向/翻盖） | 卖家或实测 | FPC 选型与折弯 |

> **建议**：板子到货当天，用卡尺把上述四项量出来回填 `parameters.json`，即可开腔体建模。在此之前**只做不依赖板体的零件**（轴承座、舵机架、轮毂、带轮、短颈、滑盖、按钮帽、线夹、配合样片）。

---

## 7. 参考链接

| 资源 | 地址 |
|---|---|
| 官方文档站（主体） | https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx |
| 资源与文档 | https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents |
| 原理图 V1 | https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-XXXX-schematic.pdf |
| **原理图 Rev1.1** | https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf |
| **BSP 源码（引脚真源）** | https://github.com/waveshareteam/ESP32-S3-CAM-OVxxxx |
| 引脚定义头文件 | `examples/ESP-IDF-v5.5.1/04_dvp_camera_display/components/waveshare__esp32_s3_cam_ovxxxx/include/bsp/esp32_s3_cam_ovxxxx.h` |
| 屏驱动定义 | 同上目录 `display.h` |

> 注：`www.waveshare.com/wiki/...` 仍显示「Wiki resources are under urgent production」，**不要等 wiki**——源码与原理图 PDF 已够用。
