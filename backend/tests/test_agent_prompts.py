"""Agent 系统提示词测试。"""

from app.agent.prompts import (
    DETECTION_AGENT_SYSTEM_PROMPT,
    RAG_QA_PROMPT,
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
    assert "attachment_id" in DETECTION_AGENT_SYSTEM_PROMPT
    assert "不要编造信息" in RAG_QA_PROMPT
    assert "stub=true" in SUPERVISOR_SYSTEM_PROMPT
