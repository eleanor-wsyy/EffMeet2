"""Qwen (DashScope) client skeleton.

Default mode is "mock" — no real API calls. Set QWEN_API_KEY environment
variable to switch to real DashScope API calls. API key is read from
environment only, never hardcoded or sent to frontend/firmware.
"""
import os
from typing import Optional

from .contracts import DemoError


class QwenAnalyzer:
    """Analyzer that calls Qwen via DashScope when QWEN_API_KEY is set.

    Falls back to mock mode when no API key is available.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("QWEN_API_KEY")
        self.mode = "real" if self._api_key else "mock"

    def analyze_viewpoints(self, utterances: list[dict]) -> list[dict]:
        """Analyze utterances and return viewpoint-response relationships.

        Args:
            utterances: List of UtteranceFinal dicts with speaker_id, text, channel.

        Returns:
            List of viewpoint dicts matching the Viewpoint schema.

        Raises:
            DemoError: If the API call fails and no fallback is available.
        """
        if self.mode == "mock":
            return self._mock_analyze(utterances)
        return self._call_dashscope(utterances)

    def _mock_analyze(self, utterances: list[dict]) -> list[dict]:
        """Deterministic mock: no real model call, no semantic judgment."""
        return [
            {
                "speaker_id": u["speaker_id"],
                "text": u["text"],
                "evidence_ids": [u["utterance_id"]],
                "response_status": "no_analysis",
                "response_evidence_ids": [],
            }
            for u in utterances
            if u.get("speaker_id")
        ]

    def _call_dashscope(self, utterances: list[dict]) -> list[dict]:
        """Call DashScope API (qwen-plus) for viewpoint analysis.

        TODO: Implement when API key and network are available.
        - Endpoint: https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
        - Model: qwen-plus
        - Input: serialized utterances with speaker labels
        - Output: JSON array of viewpoints with response_status
        - API key sent as Bearer token in Authorization header only
        """
        raise DemoError(
            501,
            "QWEN_NOT_IMPLEMENTED",
            "千问云端分析尚未接入，当前使用模拟分析。",
        )


def create_analyzer() -> QwenAnalyzer:
    """Factory: create the appropriate analyzer based on environment."""
    return QwenAnalyzer()
