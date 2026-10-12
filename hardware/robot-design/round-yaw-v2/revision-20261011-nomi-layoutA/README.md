# EffMeet2 · NOMI／布局A · v4工程候选

本轮把GOOUU换板、PLA Matte和NOMI造型落实到**真实Blender候选模型、渲染图纸和安装文档**。旧v2文件保留，当前尺寸源只维护 [../parameters.json](../parameters.json)，采购只维护 [BOM §12](../BOM.md#final-purchase-decision)。

**发布边界：可逆封装／外观候选；不是最终制造CAD，不是实机功能已通过。** 部分支架／传动仍有显式代理，打印和硬件状态保持false。

## 先看成果

- [主视觉／CMF意向板](drawings/01_主视觉_CMF.png)
- [正面／侧面／顶部及名义尺寸图](drawings/02_三视图_名义尺寸.png)
- [实际模型分解布局／内舱说明板](drawings/03_分解与内舱布局.png)
- [Blender模型](EffMeet2_NOMI_布局A_工程候选_v4.blend)，打开默认N4_NOMI_LAYOUT_A_CANDIDATE场景
- [完整渲染目录](renders/review-05/01_hero.png)：hero、front、side、top、rear、左／右45°、内部、分解与线框，共10张

图纸是由本轮真实模型生成，不是AI画出来的机构。分解图中的电子件／轴承座／带轮为封装代理；**不能称作制造装配爆炸图**。图纸标注名义尺寸，不用于施工或直接机加工。

**当前已改用GOOUU已下单套装。扩展板未量尺寸，不在本轮放得下的结论内；核心板直连仅是当前候选，扩展板可作台架工具。屏尺寸预算和GPIO／电池路径见工程复核。**

## 修改内容

- 单一连续圆润头壳、Ø106圆黑脸，真实矩形屏窗及背侧屏边让位；两只暖白眼睛只位于套装2.8TFT预算屏有效区。
- 小镜头和圆润隐私遮盖位置；短颈不增俯仰、不做360°。
- 头壳底部3.2mm接收面、隐藏Ø62法兰、两处M3候选孔、Ø22过轴及阶梯D接收；非最终公差放行。
- 双6806分置与侧置位置舵机，1:1带传动改为可容纳30mm空心轴的64T候选包络。
- 后部竖置62.6×28.3GOOUU核心板、固定INMP441×2、外接MAX98357／TP4056、右下电池、前扬声器；四条实际声槽、后通风／供电线口、麦孔、停止键与状态窗。
- 原生Screw／Boolean／Lattice／Solidify均保留；所有头部布尔控制随同一yaw姿态锚点，不覆盖旧场景。

## 检查证据与限制

- [评估外壳网格](production/evaluated-shells.json)：五个外壳／颈部件，闭合、无非流形／退化面、各一连通分量。
- [名义容纳](production/nominal-fit.json)：十五个采购／机构预留盒位于解析内轮廓；不等于全件装配／工具／线缆检查。
- [三姿态检查](production/yaw-candidate-audit.json)：-45/0/+45度头壳体积一致，头壳至底座约14mm竖向间隙；不是FPC动态或电机验收。
- [原场景保护](production/protected-scene-check.json)，[综合报告](production/validation_report.json)保留制造／硬件未放行。
- [工程复核与实测回填](ENGINEERING_REVIEW.md)，[来源](SOURCES.md)。

独立评估网格审计还提示低于打印尺度的布尔短边／小面，详见[independent-validator-raw](production/independent-validator-raw.json)；制造导出前需要清理，不能称全网格／制造检查通过。

待完成：实物屏厚／相机／线材、独立电子支架、滑盖导向防脱、分体轴承座到底座的承力固定、轴向锁定、带轮齿形／舵盘／张紧、公差样片与26项实机验收。所有未知项都不是PASS。

## 团队统一入口

**[打印件拆分方案（交给建模接管方）](SPLIT_PLAN.md)** · [安装指南](../ASSEMBLY_GUIDE.md) · [打印方案](../PRINT_PLAN.md) · [测试指南](../TEST_GUIDE.md) · [记录模板](../TEST_RECORD_TEMPLATE.csv) · [统一交接](../../HANDOFF.md)

旧 stl/ 已于 2026-10-12 删除；旧 build_print_parts.py 不是 v4 对应打印包。新模型仅为可逆工程候选，**本轮不生成一套伪装成放行件的STL，也不把网格改后缀冒充STEP**。

## 复建

生成源：[update_nomi_layoutA.py](update_nomi_layoutA.py)。需要Blender5.2，命令示例从仓库根运行：

~~~powershell
$env:EFFMEET_REVIEW='your-new-review-id'
blender --background 'hardware/robot-design/round-yaw-v2/EffMeet2_圆润转头版_封装布局_v2.blend' --python 'hardware/robot-design/round-yaw-v2/revision-20261011-nomi-layoutA/update_nomi_layoutA.py'
~~~

新审阅目录必须为空；不要覆盖冻结渲染。生成源含显式形态／剖面控制，不是全自动参数CAD；改尺寸须同步源、重建模型和证据。源参数按功能／采购占位记录，材质和灯光为中性设计预览，真实层纹／颜色／表面质量以正式料样片为准。
