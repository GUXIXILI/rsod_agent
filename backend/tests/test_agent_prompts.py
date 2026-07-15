"""Agent 系统提示词测试。"""

from app.agent.prompts import (
    DETECTION_AGENT_SYSTEM_PROMPT,
    RAG_AGENT_SYSTEM_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT,
)


def test_detection_prompt_lists_all_detection_tools():
    for tool_name in (
        "detect_single_image",
        "detect_batch_images",
        "detect_zip_images_file",
        "detect_video_file",
    ):
        assert tool_name in DETECTION_AGENT_SYSTEM_PROMPT


def test_prompts_enforce_stub_and_grounded_results():
    assert "stub=true" in DETECTION_AGENT_SYSTEM_PROMPT
    assert "不得编造" in RAG_AGENT_SYSTEM_PROMPT
    assert "LLM_STUB_MODE=true" in SUPERVISOR_SYSTEM_PROMPT
