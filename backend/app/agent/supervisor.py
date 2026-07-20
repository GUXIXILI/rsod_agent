"""
Supervisor Agent — 意图识别与任务路由

职责：
  - 分析用户输入，识别意图
  - 路由到对应的子 Agent（detection / analysis / qa）
  - 汇总各 Agent 结果，生成最终回复
"""

import re

import openai
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SUPERVISOR_ROUTING_PROMPT
from app.core.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    """主管 Agent"""

    def __init__(self, llm):
        self.llm = llm

    def route(self, state: dict) -> dict:
        """路由：识别用户意图，决定交给哪个 Agent"""
        messages = [
            SystemMessage(content=SUPERVISOR_ROUTING_PROMPT),
            state["messages"][-1],  # 最新用户消息
        ]
        try:
            response = self.llm.invoke(messages)
            next_agent = response.content.strip().lower()
        except openai.BadRequestError as e:
            logger.warning("Supervisor route LLM 调用失败(BadRequestError)，降级为 qa: %s", e)
            return {"next_agent": "qa"}

        logger.info("Supervisor 路由决策: %s", next_agent)
        return {"next_agent": next_agent}

    def decide_next(self, state: dict) -> str:
        """条件路由：根据 Supervisor 决策跳转"""
        next_agent = state.get("next_agent", "qa")
        if "detection" in next_agent:
            return "detection"
        elif "analysis" in next_agent:
            return "analysis"
        else:
            return "qa"

    def summarize(self, state: dict) -> dict:
        """汇总：整合各 Agent 结果，生成最终回复"""
        context_parts = []
        has_knowledge = False
        knowledge_sources = []

        if state.get("detection_result"):
            context_parts.append(f"检测结果：{state['detection_result']}")

        if state.get("analysis_result"):
            context_parts.append(f"分析结果：{state['analysis_result']}")

        if state.get("qa_result"):
            qa_result = state["qa_result"]
            logger.info("qa_result 类型: %s, 内容: %s", type(qa_result).__name__, str(qa_result)[:200])
            if isinstance(qa_result, dict) and "knowledge" in qa_result:
                logger.info("进入 knowledge 分支")
                knowledge_parts = []
                seen_sources = set()
                for item in qa_result["knowledge"]:
                    knowledge_parts.append(
                        f"知识来源: {item.get('source', '未知')}, 相似度: {item.get('similarity', 0):.2f}\n"
                        f"{item.get('content', '')}"
                    )
                    source = item.get("source", "未知")
                    if source not in seen_sources:
                        seen_sources.add(source)
                        match = re.match(r'#\s+(.+)', item.get("content", ""))
                        title = match.group(1) if match else source
                        knowledge_sources.append({
                            "source": source,
                            "similarity": item.get("similarity", 0),
                            "title": title,
                            "content": item.get("content", ""),
                        })
                context_parts.append("\n---\n".join(knowledge_parts))
                has_knowledge = True
                logger.info("处理完成: has_knowledge=%s, knowledge_sources_count=%d", has_knowledge, len(knowledge_sources))
            elif isinstance(qa_result, dict) and qa_result.get("answer") == "知识库中暂无相关内容":
                logger.info("进入无知识分支")
                pass
            else:
                logger.info("进入其他分支")
                context_parts.append(f"问答结果：{qa_result}")

        user_question = state["messages"][-1].content if state.get("messages") else ""

        chat_history_text = ""
        if state.get("messages") and len(state["messages"]) > 1:
            history_messages = state["messages"][:-1]
            chat_history_lines = []
            for msg in history_messages:
                role = "用户" if hasattr(msg, 'type') and msg.type == 'human' else "AI"
                content = getattr(msg, 'content', str(msg))
                chat_history_lines.append(f"{role}: {content}")
            chat_history_text = "\n".join(chat_history_lines) + "\n\n"

        if has_knowledge:
            summary_prompt = """你是一个专业的火灾烟雾检测助手。请严格根据以下检索到的知识内容回答问题，不要使用你自己的训练数据或猜测。

知识内容：
""" + "\n".join(context_parts) + """

对话历史：
""" + chat_history_text + """
用户当前问题：""" + user_question + """

请基于以上知识内容和对话历史，用简洁、专业的中文回答用户的问题。"""
        elif context_parts:
            summary_prompt = """你是一个专业的火灾烟雾检测助手。请根据以下信息回答问题：

""" + "\n".join(context_parts) + """

对话历史：
""" + chat_history_text + """
用户当前问题：""" + user_question + """

请用简洁、专业的中文回答用户的问题。"""
        else:
            summary_prompt = """你是一个专业的火灾烟雾检测助手。

对话历史：
""" + chat_history_text + """
用户当前问题：""" + user_question + """

请基于对话历史和你的知识回答问题。"""

        try:
            response = self.llm.invoke([HumanMessage(content=summary_prompt)])
        except openai.BadRequestError as e:
            logger.warning("Supervisor summarize LLM 调用失败(BadRequestError)，降级为纯文本回复: %s", e)
            return {
                "final_response": "抱歉，AI 服务暂时不可用，请稍后重试。",
                "knowledge_sources": knowledge_sources,
                "has_knowledge": has_knowledge,
            }

        return {
            "final_response": response.content,
            "knowledge_sources": knowledge_sources,
            "has_knowledge": has_knowledge,
        }