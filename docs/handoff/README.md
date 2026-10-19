# 交接记录入口

## 最新机器人设计与采购更新

[2026-10-10圆润转头版交接](2026-10-10-robot-design-and-bom.md)。正文、BOM、模型与视觉稿统一在[hardware/robot-design](../../hardware/robot-design/README.md)。当前是设计/封装布局，不是实机功能验收。

## 软件与历史记录

[2026-10-19 GitHub 新版用户端 APP 审查](2026-10-19-github-app-review.md)：远端 `apps/web` 已重写为纯本地演示版（localStorage，不接后端/音视频/ASR/AI/硬件）；建议保留功能版 `/app/`，新版作为 UI 参考或独立演示，不直接合并。

[2026-10-19路线A远程音频链路](2026-10-19-software-route-a.md)：用户端 LiveKit 入会/按需发布麦克风/离开、服务端 token 与 relay 解耦、CSP 放行；真实服务器与两端音频仍未验收。

[2026-10-16未完成软件搭框架](2026-10-16-software-scaffold.md)：ESP32 固件骨架、LiveKit 部署骨架、连续实机验收 harness，全部 NOT-VERIFIED/NOT_RUN。

[2026-10-05软件台架交接](2026-10-05-final-handoff.md)保留当日测试和边界，不当作今日测试结果；后续软件状态需结合各模块最新交接和提交。

[装配联调计划](2026-10-07-装配联调计划.md)已补充本次外观/尺寸变化，仍是计划而非执行记录。原始采购表与旧外壳方案见[机器人设计历史档案](../../hardware/robot-design/archive/README.md)。

各记录按日期及模块判读；新增设计交接不自动表示软件、硬件或连续真人链路已经验收。
