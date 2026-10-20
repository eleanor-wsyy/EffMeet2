# 台架接线表（2026-10-21，与固件 `app_config.h` 对齐）

> 台架联调期接线基线。引脚与 `firmware/esp32/main/app_config.h` 一致；
> 装机布线冻结时以本表为准更新。舵机（MG90S）当前跳过未接。

## 电源轨

| 电源轨 | 来源 | 供给 |
|---|---|---|
| 3V3 | ESP32-S3 板载 3V3 脚 | INMP441 VDD（仅此一路） |
| 5V | ESP32-S3 板载 5V 脚 | MAX98357A VIN |
| 5V-SERVO | CH340 USB-TTL 模块的 5V 脚（插充电器，不插 PC） | MG90S 红线（待接） |
| GND | 全部共地（板子 GND + CH340 GND 相连） | 所有模块 |

## 信号线

| 模块 | 模块脚 | ESP32-S3 | 说明 |
|---|---|---|---|
| INMP441 | VDD | 3V3 | 禁接 5V |
| INMP441 | GND | GND | |
| INMP441 | SCK (BCLK) | GPIO4 | |
| INMP441 | WS | GPIO5 | |
| INMP441 | SD | GPIO6 | |
| INMP441 | L/R | GND | 左声道，必接 |
| MAX98357A | VIN | 5V | 台架取板载 5V，装机时与舵机分路 |
| MAX98357A | GND | GND | |
| MAX98357A | BCLK | GPIO15 | |
| MAX98357A | LRC (WS) | GPIO16 | |
| MAX98357A | DIN | GPIO17 | |
| MAX98357A | SD | GPIO18 | 固件门控静音 |
| MAX98357A | ± | 喇叭两线 | 4-8Ω |
| MG90S（待接） | 橙(信号) | GPIO38 | |
| MG90S（待接） | 红(5V) | CH340 模块 5V 脚 | 不经板子 5V |
| MG90S（待接） | 棕(GND) | CH340 模块 GND + 共地 | |
| WS2812 状态灯 | 板载 | GPIO48 | 内置，免接 |

## 已占用 GPIO 汇总

```
4=BCLK(麦)  5=WS(麦)  6=DIN(麦)
15=BCLK(功放)  16=WS(功放)  17=DOUT(功放)  18=功放EN
38=舵机PWM  48=状态灯
```

## 台架验证命令（串口 REPL）

- 麦：`mic`（说话/拍手看 rms/peak 跳动）——**2026-10-21 已验证**：
  安静 rms=65/peak=264，PC 蜂鸣贴近 rms=394/peak=3301，拾音有效
- 功放：`tone 880 500`（蜂鸣）——数字链路无丢帧；出声待喇叭接入
- 舵机：暂跳过，信号线接入后用命令 `led`/后续 `servo` 命令
