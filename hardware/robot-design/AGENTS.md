# 机器人设计资料协作

- 本目录的当前方案、阅读顺序与证据边界见README.md、HANDOFF.md和manifest.json。
- 当前BOM只维护round-yaw-v2/BOM.md，几何参数来自同目录parameters.json；改动时同步核对模型、BOM、说明和manifest中的尺寸/状态。不要生成分散的第二份正式BOM。
- archive为历史，不从旧尺寸、旧针数或旧外观推断当前规格；保留原始来源及更正记录。
- 明确区分AI概念图、Blender封装布局与实机/制造验收；未验证项不能改写成PASS或已完成。
- 保留模型原生Screw/Boolean控制、分件与姿态依赖；新的建模必须遵循适用Blender技能。不得用预览动画代替固件验收。
- 不提交密钥、本机工具缓存、生成接口回执、自动备份、失败审阅图或重复ZIP。

## 当前v6生成与证据

- 当前模型／源／件表以manifest.canonical_files和round-yaw-v2/revision-20261011-nomi-layoutA/print-split-v6/README.md为准（build_v6.py从v2.blend生成N6场景）；v4/v5及build_round_yaw.py、build_print_parts.py、build_print_split.py是历史源，不用于生成新版整机。
- 找打印件先看print-split-v6/README.md文件表与ASSEMBLY.md§8版本陷阱：P23/P24当前是2026-10-19 FACEFLAT大平脸（plates-merged/P23_HEAD_SHELL_FACEFLAT.stl、P24_FACE_PANEL_FACEFLAT.stl），v6r2圆脸件、candidate-stl旧件、print-split-v5整套旧编号（P01=头壳）均只作历史，不要当现行件。
- 保留Screw输入的边剖面。闭合检查应检查修改器评估结果，不为使源剖面“流形”而破坏原生生成器；独立微小短边／小面提示仍须制造导出前处理。
- 主板GOOUU套装、布局A2、灰黑PLA Matte。核心板＋摄像头＋屏在头部，麦/功放/扬声器/舵机/按键固定底座，麦不随头转。只有约11根细软线跨轴（麦/功放各一对 I2S；功放 SD 接 5V 常开、EN 不跨轴）；摄像头FPC不跨轴，禁止裁剪或加长FPC。扩展板、电池、TP4056不装入。
- 不把内部座／轮／电子件代理导出为打印件；当前仍无制造／硬件放行。

- 评估网格记录数学零面积与亚打印尺度正面积面，不能混为一谈。原始独立微特征FAIL仍保留，当前综合WARN；正式导出前必须做制造网格清理。
