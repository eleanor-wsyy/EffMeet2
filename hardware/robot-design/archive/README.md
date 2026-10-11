# 历史外观、建模与采购档案

**这里只保存历史来源，不作为当前采购/制造规格。** 当前入口：[圆润转头版BOM](../round-yaw-v2/BOM.md)、[统一交接](../HANDOFF.md)。文件中的尺寸、显示板版本、转角及针数可能已被更正，不能自动继承。

| 子目录 | 来源与用途 |
|---|---|
| [seat-card-v1](seat-card-v1/README.md) | 本轮早期席位牌封装方案、最终审阅模型及[BOM](seat-card-v1/BOM.md)；已被圆润转头方向取代 |
| legacy-enclosure | 仓库原有5张概念/模型预览图和[外壳说明v2](legacy-enclosure/EffMeet2_外壳说明_v2.md)，按历史原文保留；文件内部还引用旧路径，仅作来源记录 |
| concepts/egg-refinement-20261009 | 早期蛋形外观Image2精修，不代表当前选择 |
| concepts/alternatives-20261010 | 席位牌、圆盘、圆角三角、竖向胶囊等对比图，不是已验证可装配产品 |
| [procurement](procurement/README.md) | 10月5日通用采购表及用户10月9日分享原文副本 |
| [waveshare-board-eval-20261012](waveshare-board-eval-20261012/README.md) | 微雪 ESP32-S3-CAM-OV3660 评估（全 GPIO 表、屏选型、原理图链接）；**未采用**，主板改用 GOOUU |
| [layout-candidates-20261011](layout-candidates-20261011/README.md) | 布局 A/B 二选一候选提案全文；**已定案布局 A**，B 已否决。有效内容已并入 BOM §12 与 [MODELING_BRIEF](../round-yaw-v2/MODELING_BRIEF.md) |

Git仅保存历史最终审阅模型/视图，重复ZIP、备份、失败图和本机工具记录留本地。历史脚本保留其来源，不承诺全部可跨机器直接运行；新工作使用当前round-yaw-v2参数和说明。
