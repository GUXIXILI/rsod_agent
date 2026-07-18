import pytest
from app.services.chat_service import chat_service


@pytest.mark.parametrize("message", [
    "以后你就叫叮咚鸡了",
    "你好",
    "今天天气怎么样",
    "你会做什么",
    "介绍一下自己",
])
def test_daily_chat_should_not_match_search_knowledge(message):
    result = chat_service._match_intent(message)
    assert result is None or result["name"] != "search_knowledge"


@pytest.mark.parametrize("message", [
    "火焰检测的原理是什么",
    "YOLOv11 模型的特点",
    "如何提高检测准确率",
    "火灾烟雾检测的典型应用场景",
])
def test_professional_question_should_match_search_knowledge(message):
    result = chat_service._match_intent(message)
    assert result is not None
    assert result["name"] == "search_knowledge"


def test_tie_score_prefers_earlier_tool():
    """同分时优先返回字典中排在前面的工具"""
    result = chat_service._match_intent("YOLO 检测")
    assert result is not None
    assert result["name"] == "detect_single_image"
