"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  - 创建 LangChain ReAct Agent（create_openai_tools_agent）
  - 绑定 rsod_agent 模块化工具（detection / knowledge / stats / user）
  - 提供 chat() 同步调用 和 chat_stream() 流式调用

使用方式：
  from app.agent.detection_agent import detection_agent
  result = await detection_agent.chat("检测这张图片", history=[...])
"""
import json
from typing import AsyncGenerator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# ── Monkey-patch: 修复 _convert_message_to_dict 中 tool_calls 的 function.arguments=None 问题 ──
# 原因：LangChain AgentExecutor 在二次 LLM 调用时，消息历史中的 AIMessage.tool_calls
# 可能携带 function.arguments=None，导致 OpenAI API 返回 400 参数校验错误。
# 通过 monkey-patch _convert_message_to_dict 确保所有 LLM 调用路径（_agenerate、
# _astream、_stream 等）都经过修复。
import langchain_openai.chat_models.base as _lc_base
_original_convert_message = _lc_base._convert_message_to_dict

def _patched_convert_message_to_dict(message):
    """修复版消息转换：确保 tool_calls 中 function.arguments 不为 None"""
    result = _original_convert_message(message)
    # 修复 tool_calls 中的 function.arguments
    if "tool_calls" in result:
        for tc in result["tool_calls"]:
            if isinstance(tc, dict):
                func = tc.get("function", {})
                if isinstance(func, dict) and func.get("arguments") is None:
                    func["arguments"] = "{}"
    return result

_lc_base._convert_message_to_dict = _patched_convert_message_to_dict


class SafeArgumentsChatOpenAI(ChatOpenAI):
    """
    ChatOpenAI 安全子类：修复 tool_calls 中 function.arguments 为 None 导致 LLM API 400 错误的问题。

    背景：LangChain 的 AgentExecutor 在构造第二轮 LLM 请求时，消息历史中
    的 tool_call 消息可能包含 function.arguments=None，LLM API 要求该字段
    必须是有效 JSON 字符串，否则返回 400 错误。
    """

    @staticmethod
    def _fix_none_arguments(messages):
        """遍历消息列表，修复 tool_calls 中 function.arguments 为 None 的情况

        LangChain 在构造第二轮 LLM 请求时，消息历史中的 AIMessage.tool_calls
        可能包含 function.arguments=None，导致 OpenAI API 返回 400 参数校验错误。
        此方法在消息发送到 LLM API 前修复 None 为有效 JSON 字符串 "{}"。
        """
        import json as _json
        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                continue
            for tc in tool_calls:
                # 处理对象格式：tc.function.arguments 为 None 或空
                if hasattr(tc, "function"):
                    func = tc.function
                    if hasattr(func, "arguments"):
                        if func.arguments is None:
                            func.arguments = "{}"
                        elif isinstance(func.arguments, dict):
                            # 某些情况下 arguments 可能是 dict 而非 JSON 字符串
                            func.arguments = _json.dumps(func.arguments)
                    # 同步修复 args 字段（LangChain 内部使用）
                    if hasattr(tc, "args") and (tc.args is None or tc.args == {}):
                        tc.args = {}
                # 处理 dict 格式
                elif isinstance(tc, dict):
                    func = tc.get("function", {})
                    if isinstance(func, dict):
                        if func.get("arguments") is None:
                            func["arguments"] = "{}"
                        elif isinstance(func.get("arguments"), dict):
                            func["arguments"] = _json.dumps(func["arguments"])
                    # 同步修复 args 字段
                    if tc.get("args") is None:
                        tc["args"] = {}

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """重写异步生成方法，在发送到 LLM API 前修复 function.arguments"""
        self._fix_none_arguments(messages)
        return await super()._agenerate(messages, stop, run_manager, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """重写同步生成方法"""
        self._fix_none_arguments(messages)
        return super()._generate(messages, stop, run_manager, **kwargs)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        """重写异步流式方法（astream_events 的底层调用路径），在发送前修复 function.arguments"""
        self._fix_none_arguments(messages)
        async for chunk in super()._astream(messages, stop, run_manager, **kwargs):
            yield chunk


from app.agent.prompts import DETECTION_AGENT_SYSTEM_PROMPT
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 导入工具（在 try/except 外层，若导入失败则不绑定）
try:
    from app.agent.tools.detection_tool import (
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
    )
    from app.agent.tools.knowledge_tool import search_knowledge
    from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
    from app.agent.tools.user_tool import query_user_list

    DETECTION_TOOLS = [
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
        search_knowledge,
        query_detection_stats,
        query_detection_history,
        query_user_list,
    ]
except Exception as _tools_import_err:
    logger.error("检测工具导入失败，Agent 将以无工具模式运行: %s", _tools_import_err)
    DETECTION_TOOLS = []


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        self.available: bool = False
        self.executor: Optional[AgentExecutor] = None

        try:
            # 根据配置选择 LLM 后端
            if settings.LLM_STUB_MODE:
                logger.info("DetectionAgent 在 stub 模式下启动，跳过 LLM 初始化")
                self.available = False
                return

            if settings.USE_LOCAL_LLM:
                self.llm = SafeArgumentsChatOpenAI(
                    model=settings.OLLAMA_MODEL,
                    api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )
            else:
                self.llm = SafeArgumentsChatOpenAI(
                    model=settings.QWEN_MODEL,
                    api_key=settings.QWEN_API_KEY,
                    base_url=settings.QWEN_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", DETECTION_AGENT_SYSTEM_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )

            agent = create_openai_tools_agent(self.llm, DETECTION_TOOLS, prompt)

            self.executor = AgentExecutor(
                agent=agent,
                tools=DETECTION_TOOLS,
                max_iterations=5,
                return_intermediate_steps=True,
                verbose=False,
            )
            self.available = True
            logger.info(
                "DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS)
            )
        except Exception as e:
            logger.error("DetectionAgent 初始化失败，将以降级模式运行: %s", e)
            self.available = False
            self.executor = None

    def _build_chat_history(self, history: list) -> list:
        """将 DB 中的历史消息转为 LangChain Message 对象"""
        chat_history = []
        if not history:
            return chat_history
        for msg in history[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        return chat_history

    async def chat(self, message: str, history: list = None) -> dict:
        """
        异步调用 Agent，返回完整结果。

        Args:
            message: 用户文本消息
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"output": "...", "intermediate_steps": [...]}
        """
        if not self.available:
            raise RuntimeError("Agent 不可用，请降级为纯 LLM 调用")

        chat_history = self._build_chat_history(history)

        try:
            result = await self.executor.ainvoke(
                {"input": message, "chat_history": chat_history}
            )
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", e, exc_info=True)
            raise

    async def chat_stream(
        self, message: str, history: list = None
    ) -> AsyncGenerator:
        """
        流式调用 Agent，yield SSE 事件字典。

        Yields:
            {"type": "text_chunk", "content": "..."}   — LLM 生成的文本片段
            {"type": "tool_call", "tool": "...", "input": {...}}  — 开始调用工具
            {"type": "tool_result", "tool": "...", "result": "..."}  — 工具返回
            {"type": "error", "content": "..."}         — 出错
        """
        if not self.available:
            yield {"type": "error", "content": "Agent 不可用"}
            return

        chat_history = self._build_chat_history(history)

        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    # BUG-001: 修复 tool_calls 中 function.arguments 为 None 导致 LLM API 400 错误
                    if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            if isinstance(tc, dict):
                                if "function" in tc and tc["function"].get("arguments") is None:
                                    tc["function"]["arguments"] = "{}"
                                if "args" in tc and tc["args"] is None:
                                    tc["args"] = {}
                    if hasattr(chunk, "content") and chunk.content:
                        yield {"type": "text_chunk", "content": chunk.content}

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("Agent 工具调用: %s, input=%s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info("Agent 工具完成: %s", tool_name)
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", e, exc_info=True)
            yield {"type": "error", "content": f"Agent 执行出错：{str(e)}"}


# 全局单例
detection_agent = DetectionAgent()