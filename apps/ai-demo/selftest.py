"""在议 · effmeetbot - 自动化自检脚本 (不依赖真实 DashScope API).

测试项：
1. 合法三态各自通过 (possibly_unresponded, responded, uncertain)
2. 虚构 evidence_id 被拒 (HALLUCINATED_EVIDENCE)
3. responded 但无现场证据被拒 (RESPONSE_EVIDENCE_MISSING / RESPONSE_EVIDENCE_NOT_ONSITE)
4. uncertain 却带 proposed_text 被拒 (PROPOSED_TEXT_UNEXPECTED)
5. 超长输入被拒 (超过 12 条发言 或 超过 6000 字符)
6. 无 Key 时不产生假结果 (QWEN_NOT_CONFIGURED，严格报错)
7. 附加校验：候选提示文案为问句或指令时被拒 (PROPOSED_TEXT_INVALID)
"""

import os
import sys
from pathlib import Path

# 适配 Windows 控制台编码
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保脚本可以在当前目录直接运行，也可以从仓库根目录运行
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from app import (
    DemoError,
    call_dashscope_api,
    is_question_or_command,
    parse_transcripts,
    run_analysis_pipeline,
    validate_model_response,
)
from presets import PRESET_A, PRESET_B, PRESET_C


def test_1_valid_three_states():
    """验证合法三态各自通过."""
    print("[TEST 1] 验证合法三态各自通过...")

    # 1.1 possibly_unresponded
    utterances_a = parse_transcripts(PRESET_A["text"])
    raw_a = """{
        "status": "possibly_unresponded",
        "evidence_ids": ["u6"],
        "response_utterance_ids": [],
        "proposed_text": "满溢检测可以试试重量传感器，成本更低",
        "reason": "线上丙提出满溢检测方案，后续讨论未涉及该技术点。"
    }"""
    res_a = validate_model_response(raw_a, utterances_a, "qwen-plus")
    assert res_a["status"] == "possibly_unresponded", f"status error: {res_a['status']}"
    assert res_a["proposed_text"] == "满溢检测可以试试重量传感器，成本更低"
    assert res_a["evidence_ids"] == ["u6"]
    assert res_a["response_utterance_ids"] == []
    assert res_a["model"]["model_id"] == "qwen-plus"
    print("  [PASS] 1.1 possibly_unresponded 校验通过")

    # 1.2 responded
    utterances_b = parse_transcripts(PRESET_B["text"])
    raw_b = """{
        "status": "responded",
        "evidence_ids": ["u4", "u5"],
        "response_utterance_ids": ["u5"],
        "proposed_text": "",
        "reason": "现场甲在发言 u5 中明确回应采纳了重量传感器方案。"
    }"""
    res_b = validate_model_response(raw_b, utterances_b, "qwen-plus")
    assert res_b["status"] == "responded"
    assert res_b["proposed_text"] == ""
    assert res_b["response_utterance_ids"] == ["u5"]
    print("  [PASS] 1.2 responded 校验通过")

    # 1.3 uncertain
    utterances_c = parse_transcripts(PRESET_C["text"])
    raw_c = """{
        "status": "uncertain",
        "evidence_ids": ["u2"],
        "response_utterance_ids": [],
        "proposed_text": "",
        "reason": "转写破碎，抢话混杂，无法确认是否存在关联回应。"
    }"""
    res_c = validate_model_response(raw_c, utterances_c, "qwen-plus")
    assert res_c["status"] == "uncertain"
    assert res_c["proposed_text"] == ""
    assert res_c["response_utterance_ids"] == []
    print("  [PASS] 1.3 uncertain 校验通过")


def test_2_hallucinated_evidence_id():
    """验证虚构 evidence_id 被拒."""
    print("[TEST 2] 验证虚构 evidence_id 被拒...")
    utterances = parse_transcripts(PRESET_A["text"])

    raw_hallucinated = """{
        "status": "possibly_unresponded",
        "evidence_ids": ["u999"],
        "response_utterance_ids": [],
        "proposed_text": "观点转述",
        "reason": "测试虚构ID"
    }"""

    try:
        validate_model_response(raw_hallucinated, utterances, "qwen-plus")
        raise AssertionError("应该拦截虚构 evidence_id，但放行了！")
    except DemoError as e:
        assert e.code == "HALLUCINATED_EVIDENCE", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 成功拦截虚构 evidence_id: [{e.code}] {e.message}")


def test_3_responded_without_onsite_evidence():
    """验证 responded 但无现场证据或证据非现场被拒."""
    print("[TEST 3] 验证 responded 但无现场证据被拒...")
    utterances = parse_transcripts(PRESET_B["text"])

    # 3.1 responded 但 response_utterance_ids 为空
    raw_empty_resp = """{
        "status": "responded",
        "evidence_ids": ["u4"],
        "response_utterance_ids": [],
        "proposed_text": "",
        "reason": "已回应但没给回应ID"
    }"""
    try:
        validate_model_response(raw_empty_resp, utterances, "qwen-plus")
        raise AssertionError("应该拦截空 response_utterance_ids，但放行了！")
    except DemoError as e:
        assert e.code == "RESPONSE_EVIDENCE_MISSING", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 3.1 成功拦截 responded 空回应证据: [{e.code}] {e.message}")

    # 3.2 responded 但 response_utterance_ids 包含了线上发言 u4
    raw_remote_resp = """{
        "status": "responded",
        "evidence_ids": ["u4"],
        "response_utterance_ids": ["u4"],
        "proposed_text": "",
        "reason": "用线上发言冒充现场回应"
    }"""
    try:
        validate_model_response(raw_remote_resp, utterances, "qwen-plus")
        raise AssertionError("应该拦截线上发言冒充现场回应，但放行了！")
    except DemoError as e:
        assert e.code == "RESPONSE_EVIDENCE_NOT_ONSITE", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 3.2 成功拦截非现场回应证据: [{e.code}] {e.message}")


def test_4_uncertain_with_proposed_text():
    """验证 uncertain 却带 proposed_text 被拒."""
    print("[TEST 4] 验证 uncertain 却带 proposed_text 被拒...")
    utterances = parse_transcripts(PRESET_C["text"])

    raw_uncertain_with_text = """{
        "status": "uncertain",
        "evidence_ids": ["u2"],
        "response_utterance_ids": [],
        "proposed_text": "多余的候选提醒文案",
        "reason": "明明是不确定，却偷渡了文案"
    }"""

    try:
        validate_model_response(raw_uncertain_with_text, utterances, "qwen-plus")
        raise AssertionError("应该拦截 uncertain 状态下的 proposed_text，但放行了！")
    except DemoError as e:
        assert e.code == "PROPOSED_TEXT_UNEXPECTED", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 成功拦截 uncertain 带 proposed_text: [{e.code}] {e.message}")


def test_5_input_limits_exceeded():
    """验证超长输入被拒（条数超限与字数超限）."""
    print("[TEST 5] 验证超长输入被拒...")

    # 5.1 超过 12 条发言
    lines_13 = "\n".join(
        f"[现场] 甲(u{i}): 发言第 {i} 句测试内容。" for i in range(1, 14)
    )
    lines_13 += "\n[线上] 丙(u14): 线上发言。"
    try:
        parse_transcripts(lines_13)
        raise AssertionError("应该拦截超过 12 条发言，但放行了！")
    except DemoError as e:
        assert e.code == "INPUT_LIMIT_EXCEEDED", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 5.1 成功拦截超过 12 条发言: [{e.code}] {e.message}")

    # 5.2 超过 6000 字符
    long_text = "[线上] 丙(u1): " + ("很长的文本" * 1500)
    try:
        parse_transcripts(long_text)
        raise AssertionError("应该拦截超过 6000 字符，但放行了！")
    except DemoError as e:
        assert e.code == "INPUT_LIMIT_EXCEEDED", f"错误码不匹配: {e.code}"
        print(f"  [PASS] 5.2 成功拦截超过 6000 字符: [{e.code}] {e.message}")


def test_6_no_api_key_fails_explicitly():
    """验证无 Key 时不产生假结果（禁止 fallback 成 mock，严格报错）."""
    print("[TEST 6] 验证无 Key 时不产生假结果...")
    old_key = os.environ.get("QWEN_API_KEY")
    try:
        if "QWEN_API_KEY" in os.environ:
            del os.environ["QWEN_API_KEY"]

        utterances = parse_transcripts(PRESET_A["text"])

        # 6.1 call_dashscope_api 直接调用
        try:
            call_dashscope_api(utterances, api_key="")
            raise AssertionError("无 Key 时应该报错，但放行了！")
        except DemoError as e:
            assert e.code == "QWEN_NOT_CONFIGURED", f"错误码不匹配: {e.code}"
            print(f"  [PASS] 6.1 call_dashscope_api 拒绝无 Key: [{e.code}] {e.message}")

        # 6.2 run_analysis_pipeline UI 管线
        badge, proposed, reason, table, run_info, error_html = run_analysis_pipeline(PRESET_A["text"])
        assert "QWEN_NOT_CONFIGURED" in error_html, "UI 未展示明确错误码"
        assert "❌" in error_html, "UI 错误区域未包含错误标志"
        assert proposed == "", "无 Key 时绝不得输出 proposed_text"
        print("  [PASS] 6.2 run_analysis_pipeline 拒绝无 Key，且未展示伪造成功结果")

    finally:
        if old_key is not None:
            os.environ["QWEN_API_KEY"] = old_key


def test_7_proposed_text_question_or_command():
    """验证 proposed_text 不得为问句或指令."""
    print("[TEST 7] 验证 proposed_text 为问句或指令时被拒...")
    utterances = parse_transcripts(PRESET_A["text"])

    invalid_cases = [
        ("满溢检测可以用重量传感器吗？", "问句（以？结尾）"),
        ("现场可以回应一下吗？", "问句/提示语"),
        ("请现场回应重量传感器的问题", "指令（请现场回应）"),
        ("大家听我说，用重量传感器", "指令（大家听我说）"),
        ("请提醒现场注意重量传感器", "动作指令（请提醒）"),
    ]

    for bad_text, label in invalid_cases:
        assert is_question_or_command(bad_text) is True, f"未识别为问句或指令: {bad_text}"

        raw_bad = f"""{{
            "status": "possibly_unresponded",
            "evidence_ids": ["u6"],
            "response_utterance_ids": [],
            "proposed_text": "{bad_text}",
            "reason": "测试指令问句拒绝"
        }}"""

        try:
            validate_model_response(raw_bad, utterances, "qwen-plus")
            raise AssertionError(f"应该拦截 [{label}]，但放行了: {bad_text}")
        except DemoError as e:
            assert e.code == "PROPOSED_TEXT_INVALID", f"错误码不匹配: {e.code}"

    print("  [PASS] 成功拦截 5 类违规问句与指令提示文案")


def main():
    print("=" * 60)
    print("  在议 · effmeetbot AI Demo 自检程序 (selftest.py)")
    print("=" * 60)

    test_1_valid_three_states()
    test_2_hallucinated_evidence_id()
    test_3_responded_without_onsite_evidence()
    test_4_uncertain_with_proposed_text()
    test_5_input_limits_exceeded()
    test_6_no_api_key_fails_explicitly()
    test_7_proposed_text_question_or_command()

    print("=" * 60)
    print("ALL 7 TESTS PASSED SUCCESSFULLY! 自检全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
