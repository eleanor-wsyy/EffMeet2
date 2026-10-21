# 2026-10-21 提交验证记录

## 公网地址

| 内容 | 地址 | 状态 |
|---|---|---|
| 产品官网（静态创空间） | https://www.modelscope.cn/studios/CodyNing/effmeetbot | Running |
| 官网直连 | https://codyning-effmeetbot.ms.show/ | 可匿名访问 |
| AI 判断实验台（Gradio） | https://www.modelscope.cn/studios/CodyNing/effmeetbot-ai | Running |
| AI 实验台直连 | https://codyning-effmeetbot-ai.ms.show/ | 可匿名访问，真实调用已跑通 |

两个创空间均为公开（public），构建与运行状态由魔搭 OpenAPI 查询确认。

## 真实千问调用

模型 `qwen-plus`，DashScope 真实调用，`temperature=0.1`，结果经服务端 `AnalysisResult` 契约校验。三组预设只提供输入，界面展示模型真实返回，没有按预设名称硬编码。

| 预设 | 输入 | 真实状态 | 耗时 | 证据 | 说明 |
|---|---|---|---|---|---|
| A「可能未回应」 | 8 条 | `uncertain` | 5.5 s（本地）/ 2.5 s（公网） | 8 条 | 模型认为现场后续只讨论折叠结构，无法确认语义指向，选择弃权 |
| B「已回应」 | 8 条 | `responded` | 7.6 s | 8 条 | 现场 u5 明确承接线上 u4，u6 进一步呼应，回应证据成立 |
| C「不确定」 | 7 条 | `uncertain` | 7.3 s | 7 条 | 转写破碎、多人抢话，模型无法确认回应关系 |

记录：

- A：`f8dc7f03-d0f9-42c9-a324-1801ee697573`，reason「线上成员丙(u6)提出满溢检测宜用重量传感器…后续现场发言(u7)(u8)均围绕折叠结构展开，未提及传感器、成本或隐私等关键词，无法确认语义指向该观点。」
- B：`884bb65e-c2e8-46bf-8328-10dc36e1b12c`，reason「u5 明确肯定 u4 提出的重量传感器方案…u6 进一步呼应并确认该方案。」
- C：`cb023ba3-4a92-41ea-82b7-4b4e78a52b5a`，reason「线上成员丙两次提及‘传感器’，但现场发言均聚焦‘线头松了’‘插上试试’‘有信号了’，语义指向不充分。」

**A 的预设名称与真实结果不一致，这是有意保留的事实**：模型在证据不足时弃权，没有为了演示效果改成 `possibly_unresponded`。若需要展示正向候选，应使用更长的会议窗口重测，而不是修改结果。

## 测试

| 项目 | 结果 | 证据 |
|---|---|---|
| Python 单元测试 | PASS | 129 项，15.9 s，1 项因 LiveKit 未配置跳过 |
| 前端 Node 测试 | PASS | 32 项 |
| Gradio 自检 | PASS | 7 组：三态、虚构证据、无现场回应、uncertain 带文案、超长输入、无 Key、问句文案 |
| 公网真实调用 | PASS | 预设 A → `uncertain`，2.5 s，DashScope，契约校验通过 |
| 官网响应式 | PASS | 1440 / 390，横向溢出 0，图片 8/8 加载，链接无死链 |

## 部署方式

1. 用写权限令牌调用魔搭 OpenAPI 创建两个创空间。
2. `git push` 到 `https://modelscope.cn/studios/CodyNing/<repo>.git` 的 `master` 分支。
3. `PATCH /studios/{owner}/{repo}/settings` 设置 `sdk_type`，Gradio 通过 `/secrets` 注入 `QWEN_API_KEY`。
4. `POST /studios/{owner}/{repo}/deploy` 部署；`GET /logs/run` 核对启动日志。

## 边界

- 机器人播报与转头仍为模拟回执；整机装配与连续会议未验收。
- 官网机器人图为 v6 工程渲染，不是实机照片。
- 公共 Demo 使用免费 CPU，冷启动可能需要数十秒。
- 视频与 Spotlight 尚未制作。
