# 2026-10-10 · 圆润转头版建模与采购交接

## 给接手成员和AI的结论

从仓库README进入hardware/robot-design/README.md，再读本文件、round-yaw-v2/BOM.md与round-yaw-v2/README.md。**当前设计方向是圆润转头版，阶段为可逆封装布局；没有最终外观批准、打印放行或实机转头验收。** 本次工作是设计与资料整合，不是固件和软件功能上线。

## 本次具体更新

1. 按用户“可转、圆润、参考NOMI”的反馈，从席位牌方向改为球面头部＋短颈＋固定底座；保留旧方案供追溯。
2. 用用户指定的银河智算Image2生成主视觉。它是独立AI概念图；实际建模尺寸和细节与概念图不逐像素锁定。
3. 新建可编辑Blender封装布局：主板移到底座，LCD/摄像头随头转，独立轴承与偏置SG90留位，扬声器前向。外包络180×164×222 mm；各尺寸与假设见parameters.json。
4. 编制30项BOM，划分电子件、转头机构、外壳/声学；标注数量、位置、采购状态、核验问题和官方依据。
5. 复核并修正旧清单中的LCD V1.1资料、摄像接口针数及扬声器“官方禁止8Ω”的未经核实归因；保留旧文件但明确降为历史。
6. 将分散的assets/enclosure、hardware/enclosure和采购文档归到hardware/robot-design，补充根README、handoff导航及旧路径跳转。根目录之外不维护第二份BOM。

## 读哪些文件，分别说明什么

| 文件 | 事实/证据边界 |
|---|---|
| [BOM.md](round-yaw-v2/BOM.md) | 采购建议，不是已付款清单、现货保证或实购兼容性证明 |
| [parameters.json](round-yaw-v2/parameters.json) | 官方板形尺寸与假设厚度/预留分别标注；假设需实物确认 |
| [fit-report.json](round-yaw-v2/fit-report.json) | 6项预留盒在解析腔体内、同舱盒分离；不含真实线束、传动和声腔 |
| [yaw-clearance.json](round-yaw-v2/yaw-clearance.json) | 5°步长检查左右45°刚性头壳与底座的竖向间隙；不是完整碰撞/寿命检查 |
| [evaluated_mesh_validation.json](round-yaw-v2/production/evaluated_mesh_validation.json) | 实际评估的占位网格无非流形边及零面积面；不等于生产拓扑放行 |
| [yaw-dependency-audit.json](round-yaw-v2/production/yaw-dependency-audit.json) | -45/0/+45姿态中布尔控制随头转、壳体闭合且体积基本不变 |
| [validation_report.json](round-yaw-v2/production/validation_report.json) | 综合为WARN，列出未完成的受力、接收、传动与安装接口 |
| [stage_state.json](round-yaw-v2/production/stage_state.json) | 仍停在blockout，等待外观反馈，不得把状态改为生产完成 |

检查产生于本次建模阶段。此次目录迁移和脚本路径整理不算新增机械验收；没有重新跑软件回归测试，也没有修改控制器/网关/前端/固件业务代码。

## 已修复并留存的建模问题

- 旋转剖面最初多出一条无面轴线边，已从Screw源剖面移除；初始诊断留存。
- 头壳布尔控制最初没有随头转，极限姿态会切坏外壳；已统一父级，左右极限检查通过。失败截图和检查点只留本地，团队默认看renders/review-02及“修订”三姿态图。
- 新模型保留旧场景作为快照；默认场景为R2_ROUND_YAW_BLOCKOUT。旧.blend原文件未被改写。

## 当前不要宣称

- 不宣称SG90已稳定带载、达到NOMI的噪声或顺滑度，或可连续360°。
- 不宣称模型能直接打印装机；没有STL/STEP生产导出。
- 不把普通GPIO按钮说成硬件断麦。
- 不把AI图的屏幕、孔阵、按键、滑盖当作已完成的结构设计。
- 不把转头时间轴当固件功能；firmware/esp32当前只有README骨架。
- 不把采购搜索词/搜索页当已核验商品；不按预留盒直接采购同尺寸轴承。

## 下一步交接事项

| 工作接口 | 需要先落实 | 完成证据 |
|---|---|---|
| 结构/建模协作人 | 头壳方案反馈；轴承SKU、头部重量/惯量、受力连接、传动比、线孔、限位、安装孔与公差 | 实物图纸＋可装配模型＋受力/转角与夹线试验；角色仅为建议，不覆盖团队现有分工 |
| 硬件/固件协作人 | 实板版本和连接器、可用PWM/控制输出、供电与共地、显示/摄像连接和软限位 | 接线表、固件自检与真机负载/噪声/复位记录 |
| 采购协作人 | 盘点已有件；按BOM核套装，暂缓轴承/传动/定长跨轴排线和正式壳体 | SKU、尺寸图、价格与订单状态；到货尺寸回填参数 |
| 音频协作人 | 固定底座双麦声学通道、前向扬声器声腔、转动噪声和AEC | 原始实测记录，不因模型有孔/有密封材料就判通过 |
| 展示/视觉协作人 | 用当前主视觉；建模审阅图标明占位阶段，AI图标明概念 | 与BOM/尺寸一致的展板说明；正式爆炸图等结构接口确定后制作 |

## 历史与新旧入口

- [10月9日用户原始分享清单](archive/procurement/2026-10-09-original-shared-list.md)：原文副本，未改动来源。
- [10月5日通用采购清单](archive/procurement/2026-10-05-hardware-purchase-list.md)：历史规划。
- [席位牌v1](archive/seat-card-v1/README.md)、[旧外壳说明](archive/legacy-enclosure/EffMeet2_外壳说明_v2.md)：不作为当前外观规格。
- docs/handoff/2026-10-10-robot-design-and-bom.md只作导航；本文件是此次交接正文。
- 同步目录前已快进合并远端d052490（SQLite与台架修复、参与端去重），本次不撤销或改写该提交。
