# 10.06 联调核对记录（B）

## 联调场景核对结果

| 场景 | 测试依据 | 结果 |
|---|---|---|
| **断网恢复** | `test_event_seq_and_resume`（controller）+ `test_events_resume`（bench） | ✅ 断连后从 `after_seq` 恢复，不丢事件 |
| **重复消息** | `test_same_decision_retry_is_idempotent` + `test_concurrent_confirm_dispatches_once` + `test_job_idempotency_and_readable_while_model_running` | ✅ 同一决定重复提交不重复执行；并发确认只派发一次；同一分析任务幂等 |
| **模型超时** | `test_missing_asr_is_visible` + `test_response_requires_explicit_valid_evidence`（QwenTests） | ✅ ASR 未配置返回 `ASR_NOT_CONFIGURED`；千问未配置返回 `QWEN_NOT_CONFIGURED`；上下文变更返回 `CONTEXT_CHANGED` |
| **机器人不响应** | `test_restart_never_replays_queued_command` + `test_stop_cancels_outstanding_frame` + `test_mock_device_failure_is_visible` | ✅ 重启后不回放已排队命令；停止命令取消未完成帧；模拟设备失败可见 |
| **120 秒 TTL** | `test_expired_candidate_cannot_execute` + `test_expired_analysis_renews_with_new_revision` | ✅ 过期候选不能执行；重新分析生成新版本 |
| **本人确认隔离** | `test_other_person_cannot_confirm` + `test_body_cannot_inject_actor` + `test_remote_identity_cannot_submit_others_utterance` | ✅ 他人不能替本人确认；请求体不能注入操作者身份；远程身份不能提交他人发言 |
| **新上下文需重新分析** | `test_new_context_requires_reanalysis` + `test_changed_decision_is_conflict` | ✅ 新发言进入后旧候选失效；改变决定返回 409 |
| **音频帧校验** | `test_invalid_header_stream_length_order` + `test_roundtrip_duplicate_gap` + `test_uplink_final_binding_and_no_reuse` | ✅ 非法帧头/长度/顺序拒绝；会话不可复用；token 绑定校验 |
| **播放互斥** | `test_playback_requires_drain_receipt_and_rejects_replay` | ✅ 播放需排空回执；不支持重放 |
| **回应核对** | `test_owner_evidence_and_idempotency` + `test_cross_meeting_and_summary` + `test_queued_reminder_cancelled` | ✅ 本人勾选证据确认回应；跨会议隔离；排队提醒被取消 |

## 事件 seq 核对

- 所有 seq 由控制器服务端分配，客户端不能提交 seq
- 事件单调递增，无间隙（`test_event_seq_and_resume` 断言 `seq == range(1, len+1)`）
- 断点恢复：`after_seq=N` 返回 N 之后的事件，不重发

## 状态标注核对

| 状态 | 含义 | 测试覆盖 |
|---|---|---|
| `pending_confirmation` | 候选等待本人确认 | ✅ |
| `confirmed` | 本人已确认 | ✅ |
| `dismissed` | 本人拒绝 | ✅ |
| `expired` | 120 秒 TTL 过期 | ✅ |
| `responded` | 本人确认已回应 | ✅ |
| `queued` | 命令已排队 | ✅ |
| `playing` | 命令执行中 | ✅ |
| `completed` | 命令完成（有回执） | ✅ |
| `cancelled` | 命令被取消 | ✅ |
| `failed` | 命令失败 | ✅ |
| `PROCESS_RESTARTED` | 进程重启，不回放 | ✅ |
| `RESPONSE_VERIFIED` | 回应已核对，取消提醒 | ✅ |
| `CONTEXT_CHANGED` | 上下文变更，需重新分析 | ✅ |

## 已知限制（不阻塞联调）

- 千问真实 API 未验收（无 Key）
- ESP32 硬件未接（无实物）
- LiveKit 远程音轨未实现
- AEC/双讲未验证

## 结论

10.06 联调核对通过。61 个测试覆盖上述全部场景，无遗漏。晚间冻结后只修关键演示问题。
