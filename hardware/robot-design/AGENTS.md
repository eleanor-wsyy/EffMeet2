# 机器人设计资料协作

- 本目录的当前方案、阅读顺序与证据边界见README.md、HANDOFF.md和manifest.json。
- 当前BOM只维护round-yaw-v2/BOM.md，几何参数来自同目录parameters.json；改动时同步核对模型、BOM、说明和manifest中的尺寸/状态。不要生成分散的第二份正式BOM。
- archive为历史，不从旧尺寸、旧针数或旧外观推断当前规格；保留原始来源及更正记录。
- 明确区分AI概念图、Blender封装布局与实机/制造验收；未验证项不能改写成PASS或已完成。
- 保留模型原生Screw/Boolean控制、分件与姿态依赖；新的建模必须遵循适用Blender技能。不得用预览动画代替固件验收。
- 不提交密钥、本机工具缓存、生成接口回执、自动备份、失败审阅图或重复ZIP。

## 当前v4生成与证据

- 当前模型／源／图纸以manifest.canonical_files和round-yaw-v2/revision-20261011-nomi-layoutA/README.md为准；build_round_yaw.py和build_print_parts.py是历史源，不用于生成新版整机。
- 保留Screw输入的边剖面。闭合检查应检查修改器评估结果，不为使源剖面“流形”而破坏原生生成器；独立微小短边／小面提示仍须制造导出前处理。
- 主板GOOUU套装、固定布局A、灰黑PLA Matte。只有显示线束和CAMERA排线跨轴；禁止裁剪FPC改长度。
- 不把内部座／轮／电子件代理导出为打印件；当前仍无制造／硬件放行。

- 评估网格记录数学零面积与亚打印尺度正面积面，不能混为一谈。原始独立微特征FAIL仍保留，当前综合WARN；正式导出前必须做制造网格清理。
