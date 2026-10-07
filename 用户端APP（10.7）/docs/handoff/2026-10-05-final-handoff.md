# 2026-10-05 工作交接记录

## 今日完成

围绕音频链路、模型判断和异步通信完成软件台架开发与联调。

- 接入本地 FunASR/SenseVoiceSmall，电脑麦克风录音转为 16 kHz、单声道、16-bit PCM WAV 后完成转写入账。当前为分段录音后转写，不是实时流式识别。
- 增加浏览器麦克风录音、停止并上传入口；修复音频上传被通用请求大小限制拒绝的问题。
- 使用真实 `qwen-plus` 验证 uncertain、possibly_unresponded、responded 三种判断及证据引用。现场补充发言使用手工测试文本，不能作为多人真人识别准确率结论。
- 连续软件测试推进至音频上传 → ASR → 千问 → 本人确认接口 → 命令 queued。尚不能认定已完成用户本人网页操作及机器人实播的连续验收。
- 完成摄像头预览、拍照、预览确认上传和原图读取；视觉接口采用 DashScope OpenAI-compatible 调用，`qwen3-vl-plus` 请求返回 HTTP 200。该结果证明服务调用成功，不代表识别准确率已经评估。
- 完成异步分析任务、候选版本检查、重复决定去重、回应证据人工核对及提醒状态跟踪。
- 本日最近一次单元测试结果：61 项通过。本文档整理未重新执行测试。

## 启动说明

在项目根目录执行。控制器依赖见 `requirements.txt`；ASR 使用独立 `.venv-asr`，依赖见 `requirements-asr.txt`，首次启动可能下载模型。

终端一：

```powershell
.\.venv-asr\Scripts\python.exe scripts/run_local_asr.py
```

终端二：在同一终端预先配置 `QWEN_API_KEY`，不要将密钥写入文档或提交仓库。

```powershell
$env:FUNASR_WS_URL = "ws://127.0.0.1:10096"
$env:QWEN_MODEL = "qwen-plus"
$env:QWEN_VL_MODEL = "qwen3-vl-plus"
.\.venv\Scripts\python.exe scripts/run_bench.py
```

浏览器打开 http://127.0.0.1:8768/ 。服务仅监听本机，测试身份选择器不属于正式账号认证。

## 配置与限制

| 项目 | 当前配置或边界 |
|---|---|
| ASR | `FUNASR_WS_URL=ws://127.0.0.1:10096`；SenseVoiceSmall，CPU，单段最多 30 秒 |
| 文本模型 | `QWEN_MODEL=qwen-plus` |
| 视觉模型 | `QWEN_VL_MODEL=qwen3-vl-plus`；代码默认值仍为 qwen-vl-max，需显式设置 |
| 密钥 | `QWEN_API_KEY`，仅服务端环境变量 |
| 数据库 | 默认 `data/bench.sqlite3`；可设置 `EFFMEET_DB_PATH` |
| 上传 | 音频/图片请求上限 2 MiB；音频需符合接口 WAV 格式 |
| 输出 | queued 只表示排队，不能当作机器人播放完成 |

## 已知问题及复现

1. **413 上传失败**：提交超过 2 MiB 的录音/图片会被拒绝；缩短录音，检查格式后重新上传。更新代码后需重启台架服务。
2. **视觉 502**：此前多个模型配置出现该错误，仅凭 502 不能确定是模型权限、请求格式还是上游服务原因。当前成功配置是 `qwen3-vl-plus` 配合兼容接口；保留 HTTP 状态和脱敏错误信息定位，不输出密钥。
3. **Ctrl+C 报错**：服务运行时按键盘 Ctrl+C 停止；服务退出后输入字符串 `Ctrl+C` 会触发 PowerShell CommandNotFoundException。
4. **终端中文乱码**：部分结果显示编码异常，需核对结构化响应原文；HTTP 200 不能单独证明识别内容正确。
5. **ASR 错词**：真人录音存在错词，模型测试保留原始转写；目前样例有限，没有总体准确率结论。

复现正常流程：启动两个服务 → 新建会议 → 短录音上传 → 核对转写 → 补充现场测试发言 → 发起模型分析并查询任务 → 以观点所有者确认候选 → 核对 queued 状态。视觉流程为开启摄像头 → 拍照 → 确认上传 → 调用视觉分析接口 → 检查返回文本。

## 未完成边界

- ESP32 固件当前为骨架，真实设备 PCM 上传、播放完成回执和停止行为未验收。
- 机器人、扬声器、舵机尚未完成实机联调。
- 已实现的软件暂停/播放互斥不等于声学 AEC；AEC 回声参考通道、延迟对齐和双讲效果未实测。
- 完整 LiveKit 远程媒体链路与生产账号认证未验收。
- 实时采集 → ASR → 千问 → 用户本人网页确认 → 机器人实播 → 现场回应跟踪的连续实机验收未完成。

## 今日修改涉及模块

`services/controller/app.py`：音频上传、视觉路由及请求大小边界；`qwen_client.py`：真实模型与图片调用；`audio.js`、`camera.js`、`bench.html`：浏览器采集和台架入口；`responses.py`、`store.py`：回应证据与状态；`services/relay/`：媒体协议与播放边界；`scripts/run_local_asr.py`：本地识别服务。文件清单描述本日涉及范围，当前目录无 Git 元数据，不能据此当作精确 Git diff。

## 留存证据

- [麦克风测试](2026-10-05-microphone-test.md)
- [千问文本场景测试](2026-10-05-qwen-microphone-test.md)
- [图片上传测试](2026-10-05-image-test.md)
- [回应核对截图](2026-10-05-response-review.png)
- [摄像头页面截图](2026-10-05-camera-ui.png)

早期证据文件中的“尚未完成”表示当时状态；当前总体进度以本文件为准。连续排队与最终视觉成功结果主要来自当日联调记录，尚无独立完整验收报告。测试音频、照片、模型缓存、数据库和密钥不应随代码上传 GitHub。
