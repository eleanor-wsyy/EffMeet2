# 2026-10-21 三页面品牌统一与视觉精修

## 产物

| 页面 | 路径 | 说明 |
|---|---|---|
| 产品官网 | `docs/showcase/在议-官网.html` | 官网本地快照，805 KB，图片与字体全部内嵌 |
| AI 判断实验台 | `docs/showcase/在议-AI判断实验台.html` | 真实结果快照，306 KB |
| 手机端界面全景 | `docs/showcase/在议-手机端界面全景.html` | 10 张真实截图，811 KB |
| 本地入口 | `docs/showcase/index.html` | 三个页面的导航 |

构建脚本：`scripts/build_local_pages.py`。本地预览：`python -m http.server 8782 --directory docs/showcase`。

## 品牌系统

| Token | 值 | 来源与用途 |
|---|---|---|
| 深海军蓝 | `#0A0B27` | 从正式 Logo 提取；标题、深色章节、Footer |
| 亮蓝 | `#2857F3` | 从 Logo 右上识别元素提取；主 CTA、关键交互、焦点 |
| 暖白 | `#F7F6F2` | 沿用纸张背景 |
| 中性灰 | `#6B6B66` / `#93938C` | 辅助信息、边界说明 |
| 语义绿 | `#2F6B45` | 已实现、已回应 |
| 语义灰 | `#93938C` | 不确定、弃权 |

橙色已从品牌强调中移除，仅保留在 APP 真实截图的既有界面里（按约束未对截图改色）。

## 各页面改动

### 官网

- 导航与 Footer 使用正式 `effmeetbot` Logo（原始 PNG，未重绘、未换色）；中文「在议」独立排版。
- 首屏保留大比例机器人主视觉与「在线，不等于在场。」，主 CTA 改为亮蓝。
- Hero 双入口：
  - 主要：体验产品交互 → `https://codyning-effmeetbot.ms.show/demo/`
  - 次级：体验真实 AI 判断 → `https://www.modelscope.cn/studios/CodyNing/effmeetbot-ai`
  - 下方明确标注「产品交互为静态模拟；AI 实验台调用真实 qwen-plus；两者都不是整机实测」。
- 新增「03 / 三个价值」：信息可及（看见现场）、有效参与（让观点被回应）、协作追溯（会后回到原话），并逐项标注实现状态。
- 交互章节增加「目标交互 / EMBODIED」时序：私人候选 → 本人确认 → 适当时机 → 转头 orient → 状态灯 light → 语音提醒 speak → 回应与追溯；明确区分已实现、集成中、未验收。
- 章节重新编号：03 价值、04 交互、05 工业设计、06 边界、07 技术、08 体验。
- Footer 增加 ISGBA 机构标识与「团队所属机构署名」说明，声明不代表学校主办/认证/联合研发。
- 技术资料、GitHub、主视频均指向公网可用地址；主视频链接为 92 秒 1080p。

### AI 判断实验台

- 页眉/页脚使用正式 Logo；深蓝标题、亮蓝 CTA。
- 顶部固定说明：「本页为真实 AI 运行结果快照，交互分析请进入在线实验台。」并提供醒目按钮。
- 三组真实结果原样保留：
  - A 潜在遗漏测试 / `uncertain` / 5.5 s / 8 条证据 / f8dc7f03
  - B 已回应 / `responded` / 7.6 s / 8 条证据 / 884bb65e
  - C 不确定 / `uncertain` / 7.3 s / 7 条证据 / cb023ba3
- A 的标题改为「模型没有把它判成『可能未回应』」，避免测试场景名与结论歧义。
- 增加「为什么弃权同样重要？」说明，强调证据不足不强行判断。
- 证据图裁切为「三态结论 + reason + 证据列表」，移除在线实验台截图里的 Gradio 紫色按钮，不伪造界面。
- 页脚明确「本页为静态快照，不连接模型 API」。

### 手机端界面全景

- 页眉使用正式 Logo；深蓝/亮蓝体系；390px 下「在议」不再换行。
- 新增章节导航：核心交互 / 候选确认 / 观点地图 / 其他界面；移动端保留为第二行可横向滚动。
- 10 张真实 APP 截图全部保留，未改色、未改内容；仅调整容器、标题、间距与说明文字。
- 「可交互 / 模拟候选 / 模拟回执」状态标签改为紧凑胶囊，移动端不再拉满整行。
- 页脚增加「返回产品官网」；Demo 入口指向公网 `/demo/`。

## 链接检查

| 链接 | 结果 |
|---|---|
| `https://codyning-effmeetbot.ms.show/demo/` | 200 |
| `https://www.modelscope.cn/studios/CodyNing/effmeetbot` | 200 |
| `https://www.modelscope.cn/studios/CodyNing/effmeetbot-ai` | 200 |
| `https://codyning-effmeetbot.ms.show/docs/EffMeet2_论文依据与技术路径.pdf` | 200（URL 编码后） |
| `https://codyning-effmeetbot.ms.show/assets/film/effmeetbot-film-1080p.mp4` | 200 |
| `https://github.com/eleanor-wsyy/EffMeet2` | 200 |
| 三页之间的本地返回链接 | 文件存在 |
| 章节锚点 `#core` `#confirm` `#map` `#other` | 全部存在 |

## 验收截图

`assets/submission/screens/local/`：

- `official-desktop.png` / `official-mobile.png`
- `official-values.png` / `official-interaction.png` / `official-design.png`
- `ai-desktop.png` / `ai-mobile.png` / `ai-why.png`
- `gallery-desktop.png` / `gallery-mobile.png` / `gallery-mobile-core.png`
- `index-desktop.png`

## 仍需注意

- APP 截图保留原有橙色界面，这是真实运行证据，未按新品牌改色；APP 本身的配色迭代另开任务。
- AI 快照中的证据图为 Gradio 默认真实界面截图（已裁掉紫色按钮），不是重新绘制的界面。
- 机构完整组合标识（红色 `.ai`）未使用；当前只用简洁 ISGBA SVG，避免两套机构标识并列。
- 三个页面是本地展示快照，不连接后端；真实交互以公网 Demo 与 Gradio 实验台为准。
- 主视频链接依赖公网静态站可访问；离线打开本地页面时该链接需要联网。
