"""Generate the daily task assignment PDF for EffMeet 2."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

font_name = 'Helvetica'
for fp in [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf']:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('CF', fp, subfontIndex=0))
            font_name = 'CF'
            break
        except Exception:
            continue

navy = HexColor('#1a3a4a')
teal = HexColor('#0e7c7b')
light_bg = HexColor('#f5f7fa')
white = colors.white

title_s = ParagraphStyle('T', fontName=font_name, fontSize=22, leading=28, textColor=navy, spaceAfter=6)
sub_s = ParagraphStyle('S', fontName=font_name, fontSize=11, leading=14, textColor=HexColor('#666666'), spaceAfter=20)
h2_s = ParagraphStyle('H2', fontName=font_name, fontSize=16, leading=20, textColor=navy, spaceBefore=18, spaceAfter=8)
body_s = ParagraphStyle('B', fontName=font_name, fontSize=10, leading=14, spaceAfter=4)
cell_s = ParagraphStyle('C', fontName=font_name, fontSize=9, leading=12)
cell_h = ParagraphStyle('CH', fontName=font_name, fontSize=9, leading=12, textColor=white)

out = os.path.join(os.path.expanduser('~'), 'Desktop', 'EffMeet2-每日分工-20261005-v2.pdf')
doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

story = []
story.append(Paragraph('EffMeet 2 · 每日分工与排期', title_s))
story.append(Paragraph('2026-10-05 修订（v2）| 技术工作：A B C D | 比赛资料申报：E | 全员熟练使用 Codex', sub_s))
story.append(Paragraph('在线，不等于在场。我们做了一个帮线上的人"坐回桌边"的东西。', body_s))

# ── 角色总览 ──
story.append(Paragraph('角色总览', h2_s))
roles = [
    ['角色', '职责', '写入边界', '核心交付物'],
    ['A · 产品与提示词', '产品交互、外壳、prompt 设计\n参赛叙事与表单文案', 'assets/prompts/**\ndocs/product/**\nhardware/enclosure/**', '产品 brief、演示脚本\nprompt YAML、外壳说明\n表单文字草稿'],
    ['B · 总集成', '主账本、安全编排\n设备固件、契约、媒体中继', 'services/controller/**\nservices/relay/**\nfirmware/esp32/**\ncontracts/**', 'v1 契约、事件/权限\n配对/token、Capture\n供电/BOM、统一启动'],
    ['C · 音频与媒体', '机内音频网关\nASR、TTS、分来源媒体', 'adapters/audio/**\nadapters/media/**\nadapters/tts/**', 'audio_adapter\nFunASR adapter\nTTS 生成器、AFE 配置'],
    ['D · 远程界面', '远程产品页\n音轨权限、状态表达', 'apps/web/**\nassets/face/**', '会议页/原图/确认/时间线\nLiveKit JS 集成\n观点地图可视化'],
    ['E · 申报与测试', '比赛资料申报\n场景测试、演示证据', 'tests/**\nfixtures/**\ndocs/release/**', '20 次回归、场景日志\n演示录屏、许可台账\n作品包和提交清单'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(roles)], colWidths=[30*mm, 38*mm, 45*mm, 47*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 10.04 ──
story.append(Paragraph('10.04（昨天 · 已完成）', h2_s))
story.append(Paragraph('冻结事件结构；模拟发言→确认→播报；共享原图；可追溯观点列表。', body_s))
d4 = [
    ['人员','任务','状态'],
    ['B','冻结 v1 契约（26 schema）、mock 闭环、capture、观点地图、千问骨架、relay 骨架、42 测试全过','✅ 完成'],
    ['A','产品方案稿修订（路线A/B、宠物形态、观点地图、千问口径）','✅ 完成'],
    ['C','—','未开始'],
    ['D','—','未开始'],
    ['E','—','未开始'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(d4)], colWidths=[15*mm,110*mm,35*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 10.05 ──
story.append(Paragraph('10.05（今天）· 机内音频与媒体网关', h2_s))
story.append(Paragraph('C 优先交 PCM 收发、ASR/TTS 接口；B 接设备和模型；A 核对语义；接口冻结后交 D。', body_s))
d5 = [
    ['人员','任务','验收标准'],
    ['C','1. 交 PCM 收发接口（AudioStreamConfig 对齐）\n2. 交 FunASR adapter 接口 + 参考配置\n3. 交 TTS 生成器接口\n4. 交 AFE 配置建议 + 回声/双讲样例','USB 流和机内流输出\n同一 UtteranceFinal'],
    ['B','1. 音频会话路由+设备配对+token（已完成）\n2. relay WebSocket 骨架（已完成）\n3. 千问 DashScope 接入（已完成）\n4. 接 C 的 PCM 接口，联调音频链路\n5. 核对 C 的 AFE 配置与固件兼容','音频会话开/关正确\nPCM 帧能进控制器\n千问 mock/real 切换正常'],
    ['A','1. 核对千问 prompt 语义（qwen_client.py）\n2. 确认提示文案长度和语气\n3. 和 B/C 确认装配与交互\n4. 核对表单草稿新版（钩子句+观点地图+本人确认）','提示有证据、长度可控\n表单文案 ≤500/300 字符'],
    ['D','1. 熟悉仓库代码和契约\n2. 准备 LiveKit JS 集成方案\n3. 等 C 接口冻结后接手','能跑通 demo 页面\n理解 EventEnvelope'],
    ['E','1. 确认正式队伍名单（≤5 人）\n2. 准备比赛申报资料框架\n3. 收集开源许可信息\n4. 核对表单草稿字数','名单确认\n许可台账初版\n名称≤30 介绍≤500 AI说明≤300'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(d5)], colWidths=[15*mm,80*mm,65*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),teal),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 10.06 ──
story.append(Paragraph('10.06 · 联调与冻结', h2_s))
story.append(Paragraph('联调断网、重连、重复消息、模型超时、机器人不响应。晚间冻结功能，之后只修关键演示问题。', body_s))
d6 = [
    ['人员','任务','验收标准'],
    ['B','1. 主持联调：断网/重连/重复/超时/不响应\n2. 核对事件 seq、状态标注\n3. 晚间冻结功能','断网恢复不丢事件\n重复不重复执行\n机器人不响应有降级'],
    ['C','1. 配合联调音频链路\n2. 处理回声/双讲\n3. 确认 robot_audio 标记正确','播报不自我触发\n远程不混成现场人声'],
    ['D','1. 接管 apps/web（从 B 交接 tag）\n2. 实现会议页/原图/确认/时间线\n3. 实现 LiveKit JS 加入/离开/静音','本人确认隔离\n刷新不重复提示\n权限失败可见'],
    ['A','1. 核对产品交互全流程\n2. 确认提示文案和时机\n3. 配合 D 的 UX 实现','交互路径清楚\n文案不超长'],
    ['E','1. 准备 20 次场景测试用例表\n2. 准备演示脚本和录制计划\n3. 完善申报资料\n4. 核对作品包不含 Key/凭据','覆盖回声/断网/身份/\n取消/重启/回执'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(d6)], colWidths=[15*mm,80*mm,65*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 10.07 ──
story.append(Paragraph('10.07 · 测试、录制与提交', h2_s))
story.append(Paragraph('20 次场景测试逐次记录；录正式视频+备用录屏；提交内部首版材料。官方截止 10 月 21 日。', body_s))
d7 = [
    ['人员','任务','验收标准'],
    ['E','1. 执行 20 次场景测试\n2. 录正式演示视频+备用录屏\n3. 整理作品包和提交清单\n4. 提交申报资料','20 次全记录\n零隐藏降级\n作品包不含 Key/凭据'],
    ['B','1. 配合测试，修关键 bug\n2. 准备技术说明材料\n3. 确认演示模式标注','L0/L1/L2 降级标清'],
    ['A','1. 配合录制演示视频\n2. 核对参赛叙事和表单文字\n3. 确认字数达标','名称≤30字符\n介绍≤500字符\nAI说明≤300字符'],
    ['C','1. 配合测试音频场景\n2. 准备声学测试数据','回声/双讲有记录'],
    ['D','1. 配合测试远程界面\n2. 修界面关键 bug','界面不阻碍演示'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(d7)], colWidths=[15*mm,80*mm,65*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),teal),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 10.08-10.21 ──
story.append(Paragraph('10.08 – 10.21 · 维护与迭代', h2_s))
story.append(Paragraph('正式队伍继续维护；初赛截止 10 月 21 日，可多次更新提交。', body_s))
d8 = [
    ['人员','任务'],
    ['E','持续完善申报材料，跟踪评审反馈，准备补充材料'],
    ['B','修 bug，维护仓库，推进 firmware/esp32 固件'],
    ['A','根据测试反馈优化产品文案和 prompt'],
    ['C','优化音频质量，完善 ASR/TTS 集成'],
    ['D','优化远程界面体验，完善观点地图可视化'],
]
t = Table([[Paragraph(c, cell_h if i==0 else cell_s) for c in row] for i, row in enumerate(d8)], colWidths=[15*mm,145*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('GRID',(0,0),(-1,-1),0.5,HexColor('#ccc')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light_bg]),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
story.append(t)

# ── 关键规则 ──
story.append(Paragraph('关键产品规则（与代码实现一致）', h2_s))
for r in [
    '未确认 AI 候选不触发播报；重复命令不重复执行。',
    '候选 120 秒未确认自动取消，过期后需重新分析生成新候选。',
    '本人确认后仍等安全停顿，执行前复核是否已得到回应。',
    '所有 seq 仅控制器分配，客户端不能提交 seq 或确认者身份。',
    'API Key 仅存服务端，不进前端、不进固件、不进 git。',
    '机内回执/本地停止；舵机不引发复位。',
]:
    story.append(Paragraph('• ' + r, body_s))

# ── 协作约定 ──
story.append(Paragraph('协作约定', h2_s))
for r in [
    '模块按目录边界和统一接口契约开发，公共字段变更先协商再同步上下游。',
    '先交独立自检与共同输入输出样例，再按阶段节点集成。',
    '每晚一个可见结果，不囤积未完成代码。',
    '遇到接口问题先查 contracts/v1/bundle.json，不要猜字段。',
    '全员熟练使用 Codex，代码审查和测试用 Codex 辅助。',
]:
    story.append(Paragraph('• ' + r, body_s))

doc.build(story)
print(f'PDF: {out} ({os.path.getsize(out)} bytes)')
