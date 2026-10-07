# 仓库导览 · 给 D（2026-10-06）

> 主仓：**https://github.com/eleanor-wsyy/EffMeet2**（以此为准；xxllx999 那份是过期快照，别用）
> 你是 D：远程界面。你的写入边界：`apps/web/**`、`assets/face/**`。其他目录只读。

## 目录地图

| 路径 | 是什么 | 你怎么用 |
|---|---|---|
| `README.md` | 项目总入口：跑通方法、协作约定 | 先读 |
| `contracts/v1/bundle.json` | 接口契约唯一正本（26 个 schema） | **查字段只看它**，别猜 |
| `docs/product/` | 产品文档区：报告 HTML、产品说明、演示脚本、判断样例与文案、审核报告、D端界面说明 | 你的任务书和文案来源都在这 |
| `docs/handoff/` | C 的 10-05 交接：变更记录、测试日志、硬件采购 | 了解工程现状用，可泛读 |
| `services/controller/` | B 的总集成：主账本、编排、demo 调试页 | **只读**。`demo.html` 是你的参考实现（简陋但逻辑对） |
| `services/relay/` | 媒体中继（LiveKit 侧） | 你接 LiveKit JS 时对照 `README.md` 和 `protocol.py` |
| `fixtures/demo/` | 演示台词 fixture（回收箱场景） | 你的界面测试数据 |
| `assets/hifi-screens/` | 高保真三屏图 | 照着做 |
| `assets/wireframes/` | 旧线框 SVG | 已被高保真取代，忽略 |
| `tests/` | 控制器测试 | 看 `test_controller.py` 了解业务规则的执行情况 |
| `apps/web/` | **你的目录**（还不存在，你建） | 自由发挥，但遵守 D 端说明的纪律 |

## 上手五步（今天照这个走）

```bash
git clone https://github.com/eleanor-wsyy/EffMeet2.git
cd EffMeet2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\run_demo.py
```

1. **跑通 B 的 mock**（上面四行命令，浏览器开 `http://127.0.0.1:8765`）——把「新建会议 → 加线上发言 → 生成候选 → 确认 → 看模拟播报」走一遍，你接的就是这套事件流
2. **读 `services/controller/demo.html`**——B 的调试页，界面丑但每条线都对：候选人确认、幂等、事件流，照它的数据结构接
3. **读契约** `contracts/v1/bundle.json` 里你今天要用的：`EventEnvelope`、`UtteranceFinal`、`Intervention`、`AnalysisResult`、`ViewpointMap`
4. **读 D 端说明 + 看三张高保真图**（本包）
5. **建 `apps/web/` 开工**：移动优先 PWA，文案抄判断样例 §3，样子照高保真图

## 硬规则（犯了会被打回）

- 界面文案一字不改抄 `判断样例与提示文案` §3；要改文案找 A
- 契约字段不确定 → 查 bundle.json；还不确定 → 问 B。**不许猜字段名**
- 候选人确认必须是**本人**：owner 校验失败要可见，不静默
- 刷新/重连后不能重复弹候选（契约保证了，你验证一遍）
- API Key、凭据永远不进前端代码

## 今天的验收线（晚间冻结前）

- [ ] 手机浏览器入会 → 看到原图+AI 描述
- [ ] 候选弹层弹出 → 点「请机器人提醒」→ 状态流转可见
- [ ] 观点地图三态正确，能点回原话
- [ ] PWA 能从主屏图标全屏启动
