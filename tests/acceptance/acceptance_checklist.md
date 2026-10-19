# 连续实机验收清单（全部 NOT_RUN）

> 状态纪律：未验证项不得改写为 PASS/已完成。每完成一项，把 `[ ]` 改 `[x]` 并在
> "证据"列附可核对材料（录音/截图/日志/回执），同步更新 `harness.py` 对应阶段的真实执行路径。
> **2026-10-19 更新**：S1/S2/S3/S6 的真实执行路径已实现。S1/S2 用真实 WAV/输入设备 +
> 真实 FunASR；S3 用真实 `qwen-plus`；S6 用真实现场音频/ASR + 真实回应核对，但候选分析
> 与本人确认使用 stub/测试身份（证据中已标注）。S4/S5 仍未实现，门槛满足也只报
> `NOT_RUN: 真实执行路径未实现`。清单只勾选已有真实证据的项，真人/真实账号项保持未勾选。

链：真实采集 → ASR → 千问判断 → 本人网页确认 → 机器人实播 → 现场回应跟踪

## S1 真实采集
- [ ] 机内麦（INMP441）或浏览器录音产出 16kHz/mono/s16le 合规 PCM —— 证据：尚未用 INMP441/浏览器采集。
- [x] 单段 ≤30s，电平/时长可核，非合成静音 —— 证据：2026-10-19 本机默认输入设备 1s、-40.7 dBFS；`data/acceptance_speech.wav` 5.72s、-25.6 dBFS；均为 16k mono s16le。
- [ ] 采集不夹带机器人自身 TTS（依赖 S5/AEC）—— 证据：

> 2026-10-19：harness S1 用 `data/acceptance_speech.wav`（Windows TTS 合成语音，
> 5.72s、-25.6 dBFS、16k mono s16le）跑出 `PASS`，证明格式/时长/电平校验与拒绝静音
> 逻辑可用；**这不是真人录音，也不是机内麦采集，机内麦/真人录音与 AEC 项仍不勾选**。

## S2 ASR
- [x] FunASR/SenseVoiceSmall 真实可达（`FUNASR_WS_URL`）—— 证据：2026-10-19 本地 `.venv-asr`，`run_local_asr.py` 就绪于 `ws://127.0.0.1:10096`，SenseVoiceSmall CPU。
- [x] 转写文本非空、可定位到具体发言（utterance_id/stream/start_ms）—— 证据：`S2_asr PASS`，文本 `满意检测，用重量传感器比摄像头便宜很多。`，`utterance_id=339d0572-e560-5793-b3dd-8314f392bd28`。
- [ ] 真人录音错词保留原始转写，不静默纠正 —— 证据：本轮输入为 TTS 合成语音，非真人；虽观察到“满溢→满意”错词被原样保留，但不勾选真人项。

> 2026-10-19：本地 `.venv-asr` 安装 `funasr==1.4.16` + SenseVoiceSmall（CPU），
> `run_local_asr.py` 在 `ws://127.0.0.1:10096` 就绪。用
> `data/acceptance_speech.wav`（TTS 语音，非真人）跑出 `S2_asr PASS`：
> 转写 `满意检测，用重量传感器比摄像头便宜很多。`，`asr_mode=real`，
> `utterance_id=339d0572-...`。ASR 把“满溢”听成“满意”并原样保留，未静默纠正。
> 因输入是 TTS 而非真人，第三项“真人录音错词”仍不勾选；前两项“真实可达/可定位”
> 已勾选并有本地证据。

## S3 千问判断
- [x] 真实 `qwen-plus` 返回 status∈{uncertain,possibly_unresponded,responded} —— 证据：2026-10-19 DashScope `qwen-plus` 返回 `uncertain`（meeting `53e48b86-...`），`provider=dashscope`。
- [x] 证据 ID 合法、归属唯一线上成员、proposed_text ≤80 字 —— 证据：5 条证据 ID 全部为本会议最终发言，`owner_speaker_id=remote_1`，`proposed_text` 为空（uncertain 不生成候选）。
- [ ] 视觉 `qwen3-vl-plus`（如走图片证据）返回可用结果 —— 证据：本轮未重跑视觉分支。

> 2026-10-19：真实千问返回 `uncertain` 并**没有生成候选**，符合“拿不准就弃权”。
> 首次重试遇到一次 `QWEN_NETWORK_ERROR`，重跑通过；Key 只走环境变量，未落盘/未打印。

## S6 现场回应跟踪
- [x] 现场回应被采集并核对 —— 证据：真实 FunASR 转写 `满意检测，用重量传感器比摄像头便宜很多。`，`asr_mode=real`；回应核对接口返回 `human_verified`（`remote_1` 测试身份操作，非真实账号）。
- [x] 观点地图 response_status 随真实回应更新 —— 证据：`viewpoint_response_status=responded`（meeting `ebd15f64-...`）。
- [ ] 线上线下看到同一张观点地图 —— 证据：未做双端浏览器实测。

> 2026-10-19：S6 机械链路 PASS；候选分析使用 stub，本人确认使用 `remote_1` 测试身份，
> **不是完整真人/真实账号验收**。

## S4 本人网页确认
- [ ] 由观点所有者**本人**在网页确认（非测试身份选择器冒充）—— 证据：
- [ ] 非本人/候选过期/上下文变更 → 正确拒绝（409/422）—— 证据：
- [ ] 确认后命令进入 queued，receipts 初始为空 —— 证据：

## S5 机器人实播
- [ ] 设备真实出声（扬声器），非台架播放器 —— 证据：
- [ ] RobotReceipt 顺序 accepted→started→completed，completed 在**物理播完**后 —— 证据：
- [ ] stop 命令能即时取消未播帧；断连/重启不自动重播 —— 证据：
- [ ] 播放期间拾音不误触发（AEC/双讲，见 S1 与固件 aec_afe）—— 证据：

## S6 现场回应跟踪
- [ ] 现场回应被采集并人工核对 —— 证据：
- [ ] 观点地图 response_status 随真实回应更新（非 mock 固定值）—— 证据：
- [ ] 线上线下看到同一张观点地图 —— 证据：

## 连续链（不断链）
- [ ] S1→S6 一次真人连续跑通，无手工补步骤 —— 证据：
- [ ] 全程 mode 标记真实（非 mock），账本 seq 连续可恢复 —— 证据：
- [ ] 与 10-05 交接"未完成边界"逐条对照销账 —— 证据：

## 关联未验收项（非本 harness 直接覆盖，需并行）
- [ ] ESP32 固件实机：PCM 上传/播放回执/停止（firmware/esp32，NOT-VERIFIED）
- [ ] 完整 LiveKit 远程媒体链路 + 生产账号鉴权（deploy/livekit，NOT-VERIFIED）
  - 2026-10-19：本地 LiveKit 房间 + `remote_1` 音轨 → relay → 真实 SenseVoiceSmall 入账 PASS（`scripts/smoke_livekit_remote_asr.py`）；生产账号/TURN/公网仍未验收。
- [ ] 声学 AEC 回声参考/延迟对齐/双讲实测（固件 aec_afe，桩）
