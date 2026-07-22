"""
对话服务
处理 Agent/Chat 会话和消息的 CRUD 业务逻辑

集成 ReAct Agent：
- LLM_STUB_MODE=true 时：使用占位逻辑，模拟 Agent 思考→工具调用→回复的流程
- LLM_STUB_MODE=false 时：使用真实的 LangChain ChatOpenAI + ReAct Agent
"""

import asyncio
import concurrent.futures
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import openai
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agent.detection_agent import detection_agent
from app.agent.memory import ConversationMemory
from app.entity.db_models import ChatSession, ChatMessage, DetectionScene, DetectionTask
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 重新检测关键词列表，用于识别用户"重新检测上次图片"类请求
REDETECT_KEYWORDS = [
    "重新检测", "再检测", "再检测一次", "重新测",
    "再测一次", "再试一次", "重新检测一遍",
]

# 模块级持久事件循环，用于在同步上下文中执行异步 Agent 调用
# 避免 asyncio.run() 每次调用后关闭事件循环导致 httpx 连接池失效
# （OpenAI 异步客户端通过 httpx.AsyncClient 维护 HTTP 连接池，
#  连接持有对事件循环的引用，关闭循环后旧连接无法清理）
_agent_event_loop = asyncio.new_event_loop()


class ChatService:
    """对话服务，集成 ReAct Agent 实现智能火灾烟雾检测对话"""

    def __init__(self):
        self.conversation_memory = ConversationMemory()

    # ── 工具名称到意图关键词的映射（用于 Stub 模式下的意图识别） ──
    _TOOL_INTENT_MAP = {
        "detect_single_image": {
            "keywords": ["检测", "识别", "图片", "图像", "照片", "单张", "单图", "这张"],
            "description": "单图火焰烟雾检测",
        },
        "detect_batch_images": {
            "keywords": ["批量", "多张", "多图", "一组", "这些图片", "批量检测"],
            "description": "批量图片检测",
        },
        "detect_zip_images_file": {
            "keywords": ["zip", "压缩包", "打包", "压缩文件", "解压"],
            "description": "ZIP 压缩包检测",
        },
        "detect_video_file": {
            "keywords": ["视频", "录像", "监控", "mp4", "avi", "摄像头"],
            "description": "视频检测",
        },
        "search_knowledge": {
            "keywords": ["知识", "原理", "怎么", "如何", "为什么", "什么", "介绍", "说明", "解释", "特点", "应用"],
            "description": "知识检索",
        },
        "query_detection_stats": {
            "keywords": ["统计", "概览", "总览", "数据", "统计数", "统计概览", "整体情况"],
            "description": "统计查询",
        },
        "query_detection_history": {
            "keywords": ["历史", "记录", "历史记录", "检测记录", "最近", "之前"],
            "description": "历史查询",
        },
        "query_user_list": {
            "keywords": ["用户", "人员", "账号", "成员", "用户列表", "谁"],
            "description": "用户查询",
        },
    }

    # ══════════════════════════════════════════════════════════════
    # 会话管理方法（保持不变）
    # ══════════════════════════════════════════════════════════════

    def create_session(self, db: Session, user_id: int, title: Optional[str] = None) -> ChatSession:
        """
        创建对话会话
        Args:
            db: 数据库会话
            user_id: 用户 ID
            title: 会话标题（可选，默认"新对话"）
        Returns:
            新创建的会话对象
        """
        session_uuid = str(uuid.uuid4())
        chat_session = ChatSession(
            user_id=user_id,
            session_uuid=session_uuid,
            title=title or "新对话",
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        logger.info(f"创建会话成功: user_id={user_id}, uuid={session_uuid}")
        return chat_session

    def get_sessions(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """获取用户会话列表（分页）"""
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
        total = query.count()
        sessions = (
            query.order_by(desc(ChatSession.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "id": s.id,
                    "session_uuid": s.session_uuid,
                    "title": s.title,
                    "status": s.status,
                    "message_count": s.message_count,
                    "last_message_at": s.last_message_at,
                    "created_at": s.created_at,
                }
                for s in sessions
            ],
        }

    def get_session_messages(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> list[dict]:
        """获取会话消息历史"""
        self._get_user_session(db, session_id, user_id)
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "agent_used": m.agent_used,
                "tool_calls": m.tool_calls,
                "tool_result": m.tool_result,
                "tokens_used": m.tokens_used,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    def send_message(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        content: str,
        files: list = None,
    ) -> dict:
        """
        发送消息并存储（集成 ReAct Agent 流程）
        Args:
            db: 数据库会话
            session_id: 会话 ID
            user_id: 用户 ID
            content: 消息内容
            files: 上传的文件列表（可选）
        Returns:
            包含 user_message 和 assistant_message 的字典
        """
        session = self._get_user_session(db, session_id, user_id)

        # 构建存储到数据库的消息内容（包含图片 URL 信息，用于多轮对话记忆）
        stored_content = content
        if files:
            file_hints = []
            for f in files:
                file_type = f.get("type", "file")
                file_url = f.get("url", "")
                file_name = f.get("name", "")
                if file_type == "image":
                    file_hints.append(f"[用户上传了图片: {file_url}]")
                elif file_type == "zip":
                    file_hints.append(f"[用户上传了ZIP压缩包: {file_url}]")
                elif file_type == "video":
                    file_hints.append(f"[用户上传了视频: {file_url}]")
                else:
                    file_hints.append(f"[用户上传了文件: {file_url} ({file_name})]")
            if file_hints:
                stored_content = "\n".join(file_hints) + "\n" + content

        # 存储用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=stored_content,
        )
        db.add(user_msg)
        db.flush()

        # 加载会话历史作为 LLM 上下文
        history_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

        # AI 回复（通过 Agent 流程生成）
        reply_content, tool_calls, tool_result, tokens_used, latency_ms = self._run_agent(
            content, history=history, files=files
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply_content,
            agent_used="react_agent",
            tool_calls=tool_calls if tool_calls else None,
            tool_result=tool_result if tool_result else None,
            tokens_used=tokens_used if tokens_used > 0 else None,
            latency_ms=latency_ms if latency_ms > 0 else None,
        )
        db.add(assistant_msg)

        # 更新会话信息
        session.message_count = (session.message_count or 0) + 2
        session.last_message_at = datetime.now(timezone.utc)
        if session.message_count == 2:
            session.title = content[:50] if len(content) > 50 else content

        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return {
            "user_message": {
                "id": user_msg.id,
                "session_id": user_msg.session_id,
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at,
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "session_id": assistant_msg.session_id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "agent_used": assistant_msg.agent_used,
                "tool_calls": assistant_msg.tool_calls,
                "tool_result": assistant_msg.tool_result,
                "created_at": assistant_msg.created_at,
            },
        }

    def delete_session(self, db: Session, session_id: int, user_id: int) -> bool:
        """删除会话（含消息级联删除）"""
        session = self._get_user_session(db, session_id, user_id)
        db.delete(session)
        db.commit()
        logger.info(f"删除会话成功: session_id={session_id}, user_id={user_id}")
        return True

    def _get_user_session(self, db: Session, session_id: int, user_id: int) -> ChatSession:
        """获取用户所属会话（验证权限）"""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        return session

    # ══════════════════════════════════════════════════════════════
    # Agent 核心逻辑
    # ══════════════════════════════════════════════════════════════

    def _run_agent(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        运行 Agent 流程，生成回复。

        根据 LLM_STUB_MODE 配置选择不同的执行路径：
        - True：使用占位模拟流程（不依赖外部 LLM API）
        - False：使用真实的 LangChain ReAct Agent

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表

        Returns:
            tuple: (回复内容, tool_calls列表, tool_result字符串, token数, 延迟毫秒数)
        """
        if settings.LLM_STUB_MODE:
            return self._run_agent_stub(content, history, files)
        else:
            return self._run_agent_real(content, history, files)

    def _run_agent_stub(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        Stub 模式：模拟 ReAct Agent 的思考→工具调用→回复流程。

        流程：
        1. 意图识别：根据关键词匹配确定用户意图
        2. 工具调用：模拟 Agent 选择合适的工具并执行
        3. 结果汇总：将工具返回结果格式化为自然语言回复

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表，每个文件包含 url/type/name 字段
        """
        start_time = time.time()
        tool_calls = []
        tool_result = ""

        normalized = content.strip()

        # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
        if files and self._has_image_file(files):
            has_detect_keyword = any(
                kw in normalized for kw in ["检测", "识别", "看看", "分析"]
            )
            if has_detect_keyword or not normalized:
                # 提取第一个图片 URL
                image_url = self._extract_first_image_url(files)
                if image_url:
                    tool_name = "detect_single_image"
                    tool_args = {"image_path": image_url}
                    tool_calls = [{"tool": tool_name, "args": tool_args}]

                    logger.info(
                        "Agent Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                        image_url,
                    )

                    try:
                        tool_result = self._invoke_tool_stub(tool_name, tool_args)
                    except Exception as e:
                        logger.exception("Agent Stub 图片检测工具调用失败: %s", e)
                        tool_result = f"工具调用失败：{str(e)}"

                    reply = self._format_agent_response(
                        user_message=normalized,
                        tool_name=tool_name,
                        tool_description="单图火焰烟雾检测",
                        tool_result=tool_result,
                    )

                    latency_ms = int((time.time() - start_time) * 1000)
                    tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)
                    return reply, tool_calls, tool_result, tokens_used, latency_ms

        # ── 步骤 1：意图识别 ──
        # 根据关键词匹配，找到最可能的工具意图
        matched_tool = self._match_intent(normalized)

        # ── 步骤 2：工具调用（模拟） ──
        if matched_tool:
            tool_name = matched_tool["name"]
            tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
            tool_calls = [{"tool": tool_name, "args": tool_args}]

            logger.info(
                "Agent Stub: 意图=%s, 工具=%s, 参数=%s",
                matched_tool["description"], tool_name, tool_args,
            )

            try:
                tool_result = self._invoke_tool_stub(tool_name, tool_args)
            except Exception as e:
                logger.exception("Agent Stub 工具调用失败: tool=%s", tool_name)
                tool_result = f"工具调用失败：{str(e)}"

            # ── 步骤 3：生成自然语言回复 ──
            reply = self._format_agent_response(
                user_message=normalized,
                tool_name=tool_name,
                tool_description=matched_tool["description"],
                tool_result=tool_result,
            )
        else:
            # 无法匹配到具体工具，使用通用回复
            reply = self._build_stub_reply(normalized, history)

        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)

        return reply, tool_calls, tool_result, tokens_used, latency_ms

    def _run_agent_real(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        真实模式：复用 DetectionAgent 单例执行对话。

        DetectionAgent 已在 detection_agent.py 中根据 settings 完成 LLM 配置，
        这里直接调用其 chat() 方法，避免重复创建 LLM 和 AgentExecutor 实例。

        如果用户上传了图片，会先在函数内调用检测工具获取完整结果，再把文字摘要
        注入提示词交给 Agent，避免把 base64 标注图送入 LLM 上下文导致 token 超限。
        """
        start_time = time.time()
        tool_calls = []
        tool_result_str = ""

        try:
            if not detection_agent.available:
                raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

            # 若用户上传图片，先直接检测并把摘要注入提示词
            if files and self._has_image_file(files):
                first_image_url = self._extract_first_image_url(files)
                if first_image_url:
                    tool_name = "detect_single_image"
                    tool_args = {"image_path": first_image_url, "conf": 0.4, "iou": 0.3}
                    tool_calls.append({"tool": tool_name, "args": tool_args})

                    try:
                        from app.agent.tools.detection_tool import detect_single_image
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            tool_result_str = executor.submit(
                                detect_single_image.invoke, tool_args
                            ).result()
                    except Exception as e:
                        logger.exception("真实模式图片预处理检测失败")
                        tool_result_str = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                    display_text = self._extract_tool_result_summary(tool_name, tool_result_str)
                    content = (
                        f"{content}\n\n【系统提示】已对用户上传的图片完成火灾烟雾检测，"
                        f"检测结果摘要如下（请不要再次调用检测工具）：\n{display_text}\n"
                        f"请直接基于以上结果回复用户。"
                    )

            # 调用 detection_agent.chat()（异步 → 同步）
            # 使用模块级持久事件循环，避免 asyncio.run() 每次关闭循环
            # 导致 httpx 连接池中的旧连接引用已关闭的循环而报错
            result = _agent_event_loop.run_until_complete(
                detection_agent.chat(content, history)
            )

            reply_content = result.get("output", "抱歉，无法处理您的请求。")

            # 提取工具调用信息（Agent 可能基于系统提示不再调用检测工具）
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                action, observation = step
                # 仅记录非检测类工具的调用，避免重复记录已预处理的图片检测
                if action.tool != "detect_single_image":
                    tool_calls.append({
                        "tool": action.tool,
                        "args": action.tool_input,
                    })
                    if isinstance(observation, str):
                        tool_result_str += observation + "\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(content) + len(reply_content) + len(tool_result_str)) // 2)

            return reply_content, tool_calls, tool_result_str.strip(), tokens_used, latency_ms

        except Exception as e:
            logger.exception("ReAct Agent 执行失败")
            reply = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
            latency_ms = int((time.time() - start_time) * 1000)
            return reply, tool_calls, tool_result_str.strip(), 0, latency_ms

    # ══════════════════════════════════════════════════════════════
    # Stub 模式辅助方法
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _has_image_file(files: list) -> bool:
        """检查文件列表中是否包含图片类型文件"""
        if not files:
            return False
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                return True
        return False

    @staticmethod
    def _extract_first_image_url(files: list) -> Optional[str]:
        """从文件列表中提取第一个图片文件的 URL"""
        if not files:
            return None
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                url = f.get("url") or f.get("data", {}).get("url", "")
                if url:
                    return url
        return None

    def _match_intent(self, content: str) -> Optional[dict]:
        """
        根据用户消息内容匹配最可能的工具意图。

        使用关键词匹配 + 得分排序，找到最匹配的工具。

        Args:
            content: 用户消息内容

        Returns:
            dict 或 None: 匹配到的工具信息 {"name": ..., "description": ...}
        """
        content_lower = content.lower()
        best_score = 0
        best_tool = None

        for tool_name, info in self._TOOL_INTENT_MAP.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword.lower() in content_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_tool = {"name": tool_name, "description": info["description"]}

        return best_tool if best_score > 0 else None

    def _extract_tool_args_from_stub(self, content: str, tool_name: str) -> dict:
        """
        从用户消息中提取工具调用参数（Stub 模式下的简单参数提取）。

        使用正则表达式提取常见参数模式。

        Args:
            content: 用户消息内容
            tool_name: 匹配到的工具名称

        Returns:
            dict: 工具参数字典
        """
        args = {}

        # 提取置信度参数（如 "置信度 0.5"、"conf=0.3"）
        conf_match = re.search(r'(?:置信度|conf(?:idence)?)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if conf_match:
            args["conf"] = float(conf_match.group(1))

        # 提取帧率参数（如 "每5帧"、"采样率10"、"帧率3"）
        frame_match = re.search(r'(?:每\s*(\d+)\s*帧|采样率[=：:\s]*(\d+)|帧率[=：:\s]*(\d+))', content)
        if frame_match:
            frame_val = next(v for v in frame_match.groups() if v is not None)
            args["frame_sample_rate"] = int(frame_val)

        # 提取 IoU 参数
        iou_match = re.search(r'(?:iou|nms)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if iou_match:
            args["iou"] = float(iou_match.group(1))

        # 提取文件路径（简单模式：匹配常见的文件路径格式）
        path_match = re.search(r'(?:路径|文件|图片|视频|zip)[=：:\s]*([^\s,，。]+\.(?:jpg|jpeg|png|bmp|mp4|avi|zip))', content, re.IGNORECASE)
        if path_match:
            path_val = path_match.group(1)
            if tool_name in ("detect_single_image",):
                args["image_path"] = path_val
            elif tool_name == "detect_video_file":
                args["video_path"] = path_val
            elif tool_name == "detect_zip_images_file":
                args["zip_path"] = path_val

        # 提取页码
        page_match = re.search(r'(?:第\s*(\d+)\s*页|page[=：:\s]*(\d+))', content, re.IGNORECASE)
        if page_match:
            page_val = next(v for v in page_match.groups() if v is not None)
            args["page"] = int(page_val)

        # search_knowledge 工具：直接使用用户消息作为查询
        if tool_name == "search_knowledge":
            args["query"] = content.strip()

        return args

    def _invoke_tool_stub(self, tool_name: str, args: dict) -> str:
        """
        在 Stub 模式下调用工具（直接调用工具函数，不经过 LLM）。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            str: 工具返回结果
        """
        from app.agent.tools.detection_tool import (
            detect_single_image,
            detect_batch_images,
            detect_zip_images_file,
            detect_video_file,
        )
        from app.agent.tools.knowledge_tool import search_knowledge
        from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
        from app.agent.tools.user_tool import query_user_list

        tool_map = {
            "detect_single_image": detect_single_image,
            "detect_batch_images": detect_batch_images,
            "detect_zip_images_file": detect_zip_images_file,
            "detect_video_file": detect_video_file,
            "search_knowledge": search_knowledge,
            "query_detection_stats": query_detection_stats,
            "query_detection_history": query_detection_history,
            "query_user_list": query_user_list,
        }

        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return f"未知工具：{tool_name}"

        # 调用工具（LangChain @tool 装饰的函数可以直接调用）
        return tool_func.invoke(args)

    def _format_agent_response(
        self,
        user_message: str,
        tool_name: str,
        tool_description: str,
        tool_result: str,
    ) -> str:
        """
        将工具调用结果格式化为自然语言回复。

        模拟 Agent 在获得工具结果后，生成用户友好的回复。
        如果 tool_result 是 detect_single_image 返回的 JSON，则提取 summary 字段展示。

        Args:
            user_message: 用户原始消息
            tool_name: 使用的工具名称
            tool_description: 工具描述
            tool_result: 工具返回的结果

        Returns:
            str: 格式化的自然语言回复
        """
        # 根据工具类型生成不同的回复前缀
        prefixes = {
            "detect_single_image": "已为您完成单图火焰烟雾检测，以下是检测结果：",
            "detect_batch_images": "已为您完成批量图片火焰烟雾检测，以下是检测结果：",
            "detect_zip_images_file": "已为您完成 ZIP 压缩包中图片的火焰烟雾检测，以下是检测结果：",
            "detect_video_file": "已为您完成视频火焰烟雾检测，以下是检测结果：",
            "search_knowledge": "已为您检索火灾烟雾检测相关知识，以下是检索结果：",
            "query_detection_stats": "已为您查询检测统计概览，以下是统计数据：",
            "query_detection_history": "已为您查询检测历史记录，以下是历史记录：",
            "query_user_list": "已为您查询系统用户列表，以下是用户信息：",
        }

        prefix = prefixes.get(tool_name, f"已为您执行{tool_description}，以下是结果：")

        # 检测工具返回 JSON 时，优先展示 summary 文字，避免把 base64 输出到聊天正文
        display_result = tool_result
        if tool_name == "detect_single_image":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "summary" in parsed:
                    display_result = parsed["summary"]
            except json.JSONDecodeError:
                pass
        elif tool_name == "search_knowledge":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict):
                    results = parsed.get("results", [])
                    summary = parsed.get("summary", "")
                    if results:
                        lines = [summary, ""]
                        for i, item in enumerate(results, 1):
                            question = item.get("question", "")
                            answer = item.get("answer", "")
                            answer_short = answer[:100] + "..." if len(answer) > 100 else answer
                            lines.append(f"{i}. {question}：{answer_short}")
                        display_result = "\n".join(lines)
                    else:
                        display_result = summary
            except (json.JSONDecodeError, TypeError):
                pass

        return f"{prefix}\n\n{display_result}"

    @staticmethod
    def _extract_tool_result_summary(tool_name: str, tool_result: str) -> str:
        """
        从工具结果中提取适合在聊天正文中展示的文字摘要。

        对于 detect_single_image 返回的 JSON，提取 summary 字段，
        避免将 base64 图片数据输出到聊天流中。
        对于 search_knowledge，从 results 数组中提取每条记录的 question 和 answer 摘要。
        """
        if tool_name == "detect_single_image":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "summary" in parsed:
                    return parsed["summary"]
            except json.JSONDecodeError:
                pass
        elif tool_name == "search_knowledge":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict):
                    results = parsed.get("results", [])
                    summary = parsed.get("summary", "")
                    if results:
                        lines = [summary, ""]
                        for i, item in enumerate(results, 1):
                            question = item.get("question", "")
                            answer = item.get("answer", "")
                            answer_short = answer[:100] + "..." if len(answer) > 100 else answer
                            lines.append(f"{i}. {question}：{answer_short}")
                        return "\n".join(lines)
                    return summary
            except (json.JSONDecodeError, TypeError):
                pass
        elif tool_name in ("query_detection_stats", "query_detection_history", "query_user_list"):
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "summary" in parsed:
                    return parsed["summary"]
            except (json.JSONDecodeError, TypeError):
                pass
        return tool_result

    @staticmethod
    def _build_stub_reply(content: str, history: list = None) -> str:
        """
        根据输入生成确定性的本地占位回复，不访问任何外部大模型服务。

        当无法匹配到具体工具意图时，使用此方法生成通用回复。
        """
        normalized = content.strip()
        if any(keyword in normalized for keyword in ("火", "烟", "告警", "检测")):
            return (
                "这是本地占位回复：已收到火灾烟雾检测相关问题。\n"
                "当前版本未连接真实大模型服务，您可以：\n"
                "1. 尝试使用更具体的检测指令，如「检测图片 xxx.jpg」\n"
                "2. 询问火灾烟雾检测相关知识，如「火焰检测的原理是什么」\n"
                "3. 查询检测统计，如「查看检测统计」\n"
                "4. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
            )
        history_hint = "，并已读取最近的会话上下文" if history else ""
        return (
            f"这是本地占位回复：已收到你的消息「{normalized[:50]}」{history_hint}。\n"
            "当前版本未连接真实大模型服务。您可以：\n"
            "1. 尝试使用检测相关指令，如「检测图片」「视频检测」「知识检索」等\n"
            "2. 查看检测统计：输入「统计概览」或「历史记录」\n"
            "3. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
        )

    # ══════════════════════════════════════════════════════════════
    # SSE 流式接口
    # ══════════════════════════════════════════════════════════════

    async def send_message_stream(self, user_id: int, data, session_id: int = None):
        """
        SSE 流式发送消息（异步生成器），集成 Agent 流程。

        内部自行创建和管理 DB Session，避免 FastAPI Depends 提前关闭连接。

        Yields SSE 事件:
        - event: start, data: {session_id, message_id}
        - event: token, data: {content: "xxx"}
        - event: tool_call, data: {tool: "xxx", args: {...}}
        - event: done, data: {tokens_used, latency_ms, message_id, tool_calls, tool_result}
        - event: error, data: {content: "xxx"}
        """
        from app.database.session import SessionLocal

        db = SessionLocal()
        user_msg_id = None
        try:
            # 获取或创建会话
            if session_id:
                session = self._get_user_session(db, session_id, user_id)
            else:
                session = self.create_session(db, user_id)

            # 构建消息内容（如果包含文件，注入文件信息提示）
            agent_content = data.content
            if data.files:
                file_hints = []
                for f in data.files:
                    file_type = f.get("type", "file")
                    file_url = f.get("url", "")
                    file_name = f.get("name", "")
                    if file_type == "image":
                        file_hints.append(f"用户上传了图片: {file_url}，请检测这张图片")
                    elif file_type == "zip":
                        file_hints.append(f"用户上传了ZIP压缩包: {file_url}，请检测压缩包中的图片")
                    elif file_type == "video":
                        file_hints.append(f"用户上传了视频: {file_url}，请检测该视频")
                    else:
                        file_hints.append(f"用户上传了文件: {file_url}（{file_name}）")
                agent_content = "\n".join(file_hints) + "\n" + data.content

            # 存储用户消息到数据库
            # 注意：DB 中存储用户原始文本（data.content），不包含文件提示
            # 文件提示仅用于当前轮次的 Agent 调用，不应进入历史记录
            # 否则后续对话中 LLM 会从历史中读取文件 URL 并再次调用检测工具，
            # 导致 base64 标注图进入上下文造成 token 溢出
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=data.content,
                agent_used="user",
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
            user_msg_id = user_msg.id

            # 加载历史上下文
            history_messages = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session.id,
                    ChatMessage.id != user_msg.id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

            # 加载 ConversationMemory 中的历史
            memory_history = self.conversation_memory.load_history(
                str(user_id), str(session.id)
            )
            # 合并记忆历史到上下文
            if memory_history:
                memory_history = [msg for msg in memory_history if msg["role"] in ("user", "assistant")]
                history = memory_history + history

            # 发送 thinking 事件（保留 start 向后兼容）
            start_data = {'session_id': session.id, 'message_id': user_msg.id}
            yield f"event: thinking\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"
            yield f"event: start\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"

            start_time = time.time()

            if settings.LLM_STUB_MODE:
                # ── Stub 模式：模拟 Agent 流式输出 ──
                # 先发送"思考中"的提示（text_chunk 新事件名，保留 token 向后兼容）
                thinking_content = '🔍 正在分析您的问题...'
                yield f"event: text_chunk\ndata: {json.dumps({'content': thinking_content}, ensure_ascii=False)}\n\n"

                # 意图识别
                normalized = agent_content.strip()
                tool_calls = []
                tool_result = ""
                full_content = ""

                # ── 重新检测关键词检测：用户未上传新图片但请求重新检测上次图片 ──
                # 从 DetectionTask 表查询最近一次有 original_url 的已完成检测任务
                redetect_handled = False
                if not data.files and any(kw in data.content for kw in REDETECT_KEYWORDS):
                    try:
                        recent_task = db.query(DetectionTask).filter(
                            DetectionTask.user_id == user_id,
                            DetectionTask.original_url.isnot(None),
                            DetectionTask.original_url != "",
                            DetectionTask.original_url.like("http%"),
                            DetectionTask.status == "completed",
                        ).order_by(DetectionTask.created_at.desc()).first()

                        if recent_task and recent_task.original_url:
                            original_url = recent_task.original_url
                            if "," in original_url:
                                original_url = original_url.split(",")[0].strip()
                            logger.info("SSE Stub 检测到重新检测请求，使用最近任务 original_url=%s", original_url)

                            tool_name = "detect_single_image"
                            tool_args = {"image_path": original_url, "conf": 0.4, "iou": 0.3}
                            tool_calls = [{"tool": tool_name, "args": tool_args}]

                            tool_start_data = {"tool": tool_name, "input": tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                from app.agent.tools.detection_tool import detect_single_image
                                tool_result = detect_single_image.invoke(tool_args)
                                json.loads(tool_result)
                            except json.JSONDecodeError:
                                logger.warning("SSE Stub 重新检测工具返回非 JSON 结果: %s", tool_result)
                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                            except Exception as e:
                                logger.exception("SSE Stub 重新检测失败: %s", e)
                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                            tool_end_data = {"tool": tool_name, "result": tool_result}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
                            result_content = "\n\n" + display_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            full_content = self._format_agent_response(
                                user_message=normalized,
                                tool_name=tool_name,
                                tool_description="单图火焰烟雾检测",
                                tool_result=tool_result,
                            )
                            redetect_handled = True
                    except Exception as e:
                        logger.warning("SSE Stub 重新检测查询 DetectionTask 失败: %s", e)

                # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
                files = data.files
                image_detected = False
                if files and self._has_image_file(files):
                    has_detect_keyword = any(
                        kw in normalized for kw in ["检测", "识别", "看看", "分析"]
                    )
                    if has_detect_keyword or not data.content.strip():
                        # 提取第一个图片 URL，直接调用单图检测
                        image_url = self._extract_first_image_url(files)
                        if image_url:
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": image_url}
                            tool_calls = [{"tool": tool_name, "args": tool_args}]

                            logger.info(
                                "SSE Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                                image_url,
                            )

                            # 发送工具开始事件
                            tool_start_data = {'tool': tool_name, 'input': tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                tool_result = self._invoke_tool_stub(tool_name, tool_args)
                                json.loads(tool_result)  # 校验返回是否为有效 JSON
                            except json.JSONDecodeError:
                                logger.warning("SSE Stub 图片检测工具返回非 JSON 结果: %s", tool_result)
                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                            except Exception as e:
                                logger.exception("SSE Stub 图片检测工具调用失败: %s", e)
                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                            # 发送工具结束事件（含完整结果，供前端解析标注图）
                            tool_end_data = {'tool': tool_name, 'result': tool_result}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                            # 发送专用工具结果事件，前端可据此渲染 DetectionResultCard
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                            # 发送文字摘要到聊天正文
                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
                            result_content = "\n\n" + display_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            full_content = self._format_agent_response(
                                user_message=normalized,
                                tool_name=tool_name,
                                tool_description="单图火焰烟雾检测",
                                tool_result=tool_result,
                            )
                            image_detected = True

                if not image_detected and not redetect_handled:
                    matched_tool = self._match_intent(normalized)

                    if matched_tool:
                        tool_name = matched_tool["name"]
                        tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
                        tool_calls = [{"tool": tool_name, "args": tool_args}]

                        # 发送工具开始事件（tool_start 新事件名，保留 tool_call 向后兼容）
                        tool_start_data = {'tool': tool_name, 'input': tool_args}
                        yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                        yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                        try:
                            tool_result = self._invoke_tool_stub(tool_name, tool_args)
                        except Exception as e:
                            logger.exception("SSE Stub 工具调用失败: tool=%s", tool_name)
                            tool_result = json.dumps({"error": f"工具调用失败：{str(e)}"}, ensure_ascii=False)

                        # 发送工具结束事件（tool_end 新事件名）
                        tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                        yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                        # 发送工具结果事件（text_chunk 新事件名，保留 token 向后兼容）
                        display_text = self._extract_tool_result_summary(tool_name, tool_result)
                        result_content = "\n\n" + display_text
                        yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                        full_content = self._format_agent_response(
                            user_message=normalized,
                            tool_name=tool_name,
                            tool_description=matched_tool["description"],
                            tool_result=tool_result,
                        )
                    else:
                        full_content = self._build_stub_reply(normalized, history)
                        # 流式输出回复内容（text_chunk 新事件名，保留 token 向后兼容）
                        for offset in range(0, len(full_content), 8):
                            chunk = full_content[offset : offset + 8]
                            yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                # ── 真实模式：复用 DetectionAgent 单例流式输出 ──
                try:
                    if not detection_agent.available:
                        raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

                    full_content = ""
                    tool_calls = []
                    tool_result = ""
                    skip_agent = False  # 图片预处理后跳过 Agent，避免 token 溢出

                    # 重新检测关键词检测：用户未上传新图片但请求重新检测上次图片
                    # 从 DetectionTask 表查询最近一次有 original_url 的已完成检测任务
                    if not data.files and any(kw in data.content for kw in REDETECT_KEYWORDS):
                        try:
                            recent_task = db.query(DetectionTask).filter(
                                DetectionTask.user_id == user_id,
                                DetectionTask.original_url.isnot(None),
                                DetectionTask.original_url != "",
                                DetectionTask.original_url.like("http%"),
                                DetectionTask.status == "completed",
                            ).order_by(DetectionTask.created_at.desc()).first()

                            if recent_task and recent_task.original_url:
                                original_url = recent_task.original_url
                                # 若 original_url 包含逗号分隔的多张图片，取第一张
                                if "," in original_url:
                                    original_url = original_url.split(",")[0].strip()
                                logger.info("检测到重新检测请求，使用最近任务 original_url=%s", original_url)

                                tool_name = "detect_single_image"
                                tool_args = {"image_path": original_url, "conf": 0.4, "iou": 0.3}
                                tool_calls.append({"tool": tool_name, "args": tool_args})

                                tool_start_data = {"tool": tool_name, "input": tool_args}
                                yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                                yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                                try:
                                    from app.agent.tools.detection_tool import detect_single_image
                                    loop = asyncio.get_event_loop()
                                    tool_result = await loop.run_in_executor(
                                        None,
                                        lambda: detect_single_image.invoke(tool_args),
                                    )
                                    json.loads(tool_result)
                                except json.JSONDecodeError:
                                    logger.warning("重新检测工具返回非 JSON 结果: %s", tool_result)
                                    tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                                except Exception as e:
                                    logger.exception("重新检测图片预处理失败")
                                    tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                                tool_end_data = {"tool": tool_name, "result": tool_result}
                                yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                                yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                                display_text = self._extract_tool_result_summary(tool_name, tool_result)
                                result_content = "\n\n" + display_text
                                yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                                try:
                                    detect_result = json.loads(tool_result)
                                    summary = detect_result.get("summary", "检测完成")
                                except (json.JSONDecodeError, TypeError):
                                    summary = "检测完成，但无法解析详细结果。"
                                full_content = f"已对上次上传的图片重新检测，结果如下：{summary}"
                                for offset in range(0, len(full_content), 8):
                                    chunk = full_content[offset:offset + 8]
                                    yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                                skip_agent = True
                        except Exception as e:
                            # 查 DB 失败不影响正常流程，让 LLM 自然回复
                            logger.warning("重新检测查询 DetectionTask 失败: %s", e)

                    # 若用户上传了图片，先直接调用检测工具，避免把 base64 标注图
                    # 送入 LLM 上下文导致 token 超限；只把文字摘要交给 Agent。
                    if data.files and self._has_image_file(data.files):
                        first_image_url = self._extract_first_image_url(data.files)
                        if first_image_url:
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": first_image_url, "conf": 0.4, "iou": 0.3}
                            tool_calls.append({"tool": tool_name, "args": tool_args})

                            tool_start_data = {"tool": tool_name, "input": tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                from app.agent.tools.detection_tool import detect_single_image
                                loop = asyncio.get_event_loop()
                                tool_result = await loop.run_in_executor(
                                    None,
                                    lambda: detect_single_image.invoke(tool_args),
                                )
                                json.loads(tool_result)  # 校验返回是否为有效 JSON
                            except json.JSONDecodeError:
                                logger.warning("真实模式图片检测工具返回非 JSON 结果: %s", tool_result)
                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                            except Exception as e:
                                logger.exception("真实模式图片预处理检测失败")
                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                            # 发送完整工具结果，前端可解析标注图
                            tool_end_data = {"tool": tool_name, "result": tool_result}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                            # 在聊天正文显示文字摘要
                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
                            result_content = "\n\n" + display_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            # 图片预处理后，检测结果已发送给前端。
                            # 跳过 Agent 调用，避免 LLM 无视指令再次调用 detect_single_image，
                            # 导致 base64 标注图进入上下文造成 token 溢出（682083 > 131072）
                            try:
                                detect_result = json.loads(tool_result)
                                summary = detect_result.get("summary", "检测完成")
                            except (json.JSONDecodeError, TypeError):
                                summary = "检测完成，但无法解析详细结果。"
                            full_content = f"根据检测结果：{summary}"
                            # 流式输出回复
                            for offset in range(0, len(full_content), 8):
                                chunk = full_content[offset:offset + 8]
                                yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                            skip_agent = True

                            # 保存 DetectionTask 记录（含 original_url），供后续"重新检测"查询使用
                            # detect_single_image 工具内部使用 user_id=1 创建记录，
                            # 此处以当前用户 ID 另存一条，确保重新检测时按 user_id 能匹配到
                            try:
                                detect_result = json.loads(tool_result)
                                fire_scene = db.query(DetectionScene).filter(
                                    DetectionScene.name == "fire_smoke",
                                    DetectionScene.is_active == True,
                                ).first()
                                scene_id = fire_scene.id if fire_scene else 1

                                file_name = None
                                if data.files:
                                    for f in data.files:
                                        if isinstance(f, dict) and f.get("type") == "image":
                                            file_name = f.get("name", "")
                                            break

                                task = DetectionTask(
                                    user_id=user_id,
                                    scene_id=scene_id,
                                    task_type="single",
                                    status="completed",
                                    file_name=file_name,
                                    original_url=first_image_url,
                                    annotated_url=detect_result.get("annotated_image", ""),
                                    total_images=1,
                                    total_objects=detect_result.get("total_detections", 0),
                                    total_inference_time=detect_result.get("inference_time", 0),
                                    conf_threshold=0.4,
                                    iou_threshold=0.3,
                                    fire_object_count=detect_result.get("fire_count", 0),
                                    smoke_object_count=detect_result.get("smoke_count", 0),
                                    detected_at=datetime.now(timezone.utc),
                                )
                                db.add(task)
                                db.flush()
                                logger.info(
                                    "已保存 DetectionTask 记录 task_id=%s original_url=%s user_id=%s",
                                    task.id, first_image_url, user_id,
                                )
                            except Exception as e:
                                logger.warning("保存 DetectionTask 记录失败（不影响主流程）: %s", e)

                    # 若未跳过 Agent（非图片消息或图片预处理失败），正常调用 Agent 流式输出
                    if not skip_agent:
                        async for event in detection_agent.chat_stream(agent_content, history):
                            event_type = event.get("type", "")

                            if event_type == "text_chunk":
                                token_text = event.get("content", "")
                                full_content += token_text
                                yield f"event: text_chunk\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"

                            elif event_type == "tool_call":
                                tool_name = event.get("tool", "")
                                tool_input = event.get("input", {})
                                # BUG-001: 防御 tool_input 为 None 的情况
                                if tool_input is None:
                                    tool_input = {}
                                tool_calls.append({"tool": tool_name, "args": tool_input})
                                tool_start_data = {'tool': tool_name, 'input': tool_input}
                                yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                                yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            elif event_type == "tool_result":
                                tool_output = event.get("result", "")
                                tool_name = event.get("tool", "")
                                if tool_output:
                                    tool_result += str(tool_output) + "\n"
                                    # 发送完整工具结果，前端可解析标注图
                                    tool_end_data = {'tool': tool_name, 'result': tool_output}
                                    yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                                    yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_output}, ensure_ascii=False)}\n\n"

                            elif event_type == "error":
                                error_content = event.get("content", "") or event.get("message", "")
                                if not error_content:
                                    error_content = "AI 服务暂时不可用，请稍后重试。"
                                yield f"event: error\ndata: {json.dumps({'content': error_content}, ensure_ascii=False)}\n\n"

                    if not full_content:
                        full_content = "抱歉，无法处理您的请求。"

                except openai.BadRequestError as e:
                    logger.error("SSE Agent 执行失败(BadRequestError): %s", str(e), exc_info=True)
                    full_content = "AI 服务暂时不可用，请稍后重试。"
                    tool_calls = []
                    tool_result = ""
                    yield f"event: error\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    logger.exception("SSE Agent 执行失败")
                    full_content = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
                    tool_calls = []
                    tool_result = ""
                    yield f"event: error\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(data.content) + len(full_content)) // 2)

            # 存储 AI 回复到数据库
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                agent_used="react_agent",
                tool_calls=tool_calls if tool_calls else None,
                tool_result=tool_result if tool_result else None,
                tokens_used=tokens_used if tokens_used > 0 else None,
                latency_ms=latency_ms if latency_ms > 0 else None,
            )
            db.add(assistant_msg)

            # 更新会话
            session.message_count = (session.message_count or 0) + 2
            session.last_message_at = datetime.now(timezone.utc)
            if session.message_count == 2:
                session.title = data.content[:50] if len(data.content) > 50 else data.content
            db.commit()
            db.refresh(assistant_msg)

            # 保存到 ConversationMemory
            try:
                self.conversation_memory.save_message(
                    str(user_id), str(session.id), "user", data.content
                )
                self.conversation_memory.save_message(
                    str(user_id), str(session.id), "assistant", full_content
                )
            except Exception as e:
                logger.warning("保存对话记忆失败（不影响主流程）: %s", e)

            # 发送 done 事件，包含 session_id 以便前端自动关联新会话
            done_data = {
                "session_id": session.id,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "message_id": assistant_msg.id,
                "tool_calls": tool_calls if tool_calls else [],
                "tool_result": tool_result if tool_result else "",
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            db.rollback()
            logger.error("SSE流式输出错误: %s", e)
            yield f"event: error\ndata: {json.dumps({'content': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
        finally:
            db.close()

    async def send_message_stream_multi_agent(self, user_id: int, data, session_id: int = None):
        """
        SSE 流式发送消息（多Agent 编排模式），使用 LangGraph Supervisor 路由架构。

        内部自行创建和管理 DB Session。
        如果 LangGraph 初始化失败，自动降级到 send_message_stream 单Agent模式。

        Yields SSE 事件:
        - event: thinking, data: {session_id, message_id}
        - event: agent_chain, data: {agents: ["supervisor","detection","summarize"], current: "detection"}
        - event: text_chunk, data: {content: "xxx"}
        - event: knowledge_sources, data: {sources: [...]}
        - event: done, data: {tokens_used, latency_ms, message_id}
        - event: error, data: {content: "xxx"}
        """
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            # 获取或创建会话
            if session_id:
                session = self._get_user_session(db, session_id, user_id)
            else:
                session = self.create_session(db, user_id)

            # 构建消息内容
            agent_content = data.content
            if data.files:
                file_hints = []
                for f in data.files:
                    file_type = f.get("type", "")
                    file_url = f.get("url", "")
                    file_name = f.get("name", "")
                    if file_type == "image":
                        file_hints.append(f"[附件图片路径: {file_url}]")
                    elif file_type == "zip":
                        file_hints.append(f"[附件ZIP路径: {file_url}]")
                    elif file_type == "video":
                        file_hints.append(f"[附件视频路径: {file_url}]")
                    else:
                        file_hints.append(f"[附件文件: {file_url}（{file_name}）]")
                agent_content = "\n".join(file_hints) + "\n" + data.content

            # 存储用户消息
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=data.content,
                agent_used="user",
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)

            # 加载历史上下文
            history_messages = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session.id,
                    ChatMessage.id != user_msg.id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

            # 加载 ConversationMemory 中的历史
            memory_history = self.conversation_memory.load_history(
                str(user_id), str(session.id)
            )
            if memory_history:
                memory_history = [msg for msg in memory_history if msg["role"] in ("user", "assistant")]
                history = memory_history + history

            # 发送 thinking 事件
            start_data = {'session_id': session.id, 'message_id': user_msg.id}
            yield f"event: thinking\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"

            start_time = time.time()

            try:
                # ── 重新检测逻辑：用户未上传新图片但请求重新检测上次图片 ──
                # 从 DetectionTask 表查询最近一次有 original_url 的已完成检测任务
                if not data.files and any(kw in data.content for kw in REDETECT_KEYWORDS):
                    try:
                        recent_task = db.query(DetectionTask).filter(
                            DetectionTask.user_id == user_id,
                            DetectionTask.original_url.isnot(None),
                            DetectionTask.original_url != "",
                            DetectionTask.original_url.like("http%"),
                            DetectionTask.status == "completed",
                        ).order_by(DetectionTask.created_at.desc()).first()

                        if recent_task and recent_task.original_url:
                            original_url = recent_task.original_url
                            if "," in original_url:
                                original_url = original_url.split(",")[0].strip()
                            logger.info("多Agent 检测到重新检测请求，使用最近任务 original_url=%s", original_url)

                            # 直接调用检测工具（不经过 Supervisor 路由和 LLM）
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": original_url, "conf": 0.4, "iou": 0.3}

                            tool_start_data = {"tool": tool_name, "input": tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            from app.agent.tools.detection_tool import detect_single_image
                            try:
                                loop = asyncio.get_event_loop()
                                tool_result_str = await loop.run_in_executor(
                                    None,
                                    lambda: detect_single_image.invoke(tool_args),
                                )
                                detect_result = json.loads(tool_result_str)
                            except json.JSONDecodeError:
                                logger.warning("重新检测工具返回非 JSON 结果: %s", tool_result_str)
                                detect_result = {"error": "工具返回了非 JSON 结果"}
                            except Exception as e:
                                logger.exception("重新检测图片预处理失败")
                                detect_result = {"error": f"检测失败：{str(e)}"}

                            # 提取标注图数据，发送 annotation_image 事件
                            annotation_data = None
                            if "annotated_image_base64" in detect_result:
                                annotation_data = {
                                    "annotated_image_base64": detect_result.pop("annotated_image_base64"),
                                    "annotated_image_url": detect_result.get("annotated_image_url", ""),
                                    "summary": detect_result.get("summary", ""),
                                    "fire_level": detect_result.get("fire_level", ""),
                                    "fire_object_count": detect_result.get("fire_object_count", 0),
                                    "smoke_object_count": detect_result.get("smoke_object_count", 0),
                                    "total_objects": detect_result.get("total_objects", 0),
                                }
                            if annotation_data:
                                yield f"event: annotation_image\ndata: {json.dumps(annotation_data, ensure_ascii=False)}\n\n"

                            # 发送工具结束事件
                            tool_end_data = {"tool": tool_name, "result": json.dumps(detect_result, ensure_ascii=False)}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': json.dumps(detect_result, ensure_ascii=False)}, ensure_ascii=False)}\n\n"

                            # 发送文字摘要
                            summary = detect_result.get("summary", "检测完成")
                            full_content = f"已对上次上传的图片重新检测，结果如下：\n{summary}"
                            for offset in range(0, len(full_content), 8):
                                chunk = full_content[offset:offset + 8]
                                yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                            # 跳过后续 LangGraph 流程
                            skip_graph = True
                        else:
                            logger.info("未找到可重新检测的任务，走正常多Agent流程")
                            skip_graph = False
                    except Exception as e:
                        logger.warning("重新检测查询 DetectionTask 失败: %s", e)
                        skip_graph = False
                else:
                    skip_graph = False

                if not skip_graph:
                    # 尝试构建 LangGraph 多Agent 工作流
                    from app.agent.graph import build_agent_graph
                    from app.agent.nodes import detection_node, analysis_node, qa_node
                    from langchain_core.messages import HumanMessage, SystemMessage

                    # 获取 LLM 实例
                    from app.agent.detection_agent import detection_agent
                    if not detection_agent.available:
                        raise RuntimeError("DetectionAgent 不可用，降级到单Agent模式")

                    llm = detection_agent.llm
                    if not llm:
                        raise RuntimeError("LLM 未初始化，降级到单Agent模式")

                    # 构建图
                    graph = build_agent_graph(llm, detection_node, analysis_node, qa_node)

                    # 准备初始状态
                    initial_state = {
                        "messages": [HumanMessage(content=agent_content)],
                        "user_id": user_id,
                        "session_id": str(session.id),
                    }

                    # 发送 agent_chain 事件：开始 Supervisor 路由
                    chain_data = {
                        "agents": ["supervisor", "detection", "analysis", "qa", "summarize"],
                        "current": "supervisor",
                        "status": "routing",
                    }
                    yield f"event: agent_chain\ndata: {json.dumps(chain_data, ensure_ascii=False)}\n\n"

                    full_content = ""
                    knowledge_sources = []

                    # 流式执行 LangGraph
                    async for event in graph.astream(initial_state):
                        for node_name, node_output in event.items():
                            # 发送 agent_chain 事件
                            chain_data = {
                                "agents": ["supervisor", "detection", "analysis", "qa", "summarize"],
                                "current": node_name,
                                "status": "running",
                            }
                            yield f"event: agent_chain\ndata: {json.dumps(chain_data, ensure_ascii=False)}\n\n"

                            if node_name == "supervisor":
                                next_agent = node_output.get("next_agent", "unknown")
                                logger.info("Supervisor 路由到: %s", next_agent)

                            elif node_name == "detection":
                                detection_result = node_output.get("detection_result", {})
                                annotation_data = node_output.get("annotation_data", {})

                                if detection_result and not detection_result.get("error"):
                                    # 检测成功：发送标注图数据给前端
                                    if annotation_data:
                                        yield f"event: annotation_image\ndata: {json.dumps(annotation_data, ensure_ascii=False)}\n\n"

                                    # 发送检测结果文字摘要
                                    summary = detection_result.get("summary", "检测完成")
                                    result_content = "\n\n" + summary
                                    yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                                    full_content = summary
                                    logger.info("Detection 成功，已直接发送结果（跳过 summarize）")
                                else:
                                    error_msg = detection_result.get("error", "检测失败")
                                    yield f"event: text_chunk\ndata: {json.dumps({'content': f'检测完成，但出现问题：{error_msg}'}, ensure_ascii=False)}\n\n"

                            elif node_name == "analysis":
                                analysis_result = node_output.get("analysis_result", {})
                                if analysis_result:
                                    yield f"event: text_chunk\ndata: {json.dumps({'content': '分析完成...'}, ensure_ascii=False)}\n\n"

                            elif node_name == "qa":
                                qa_result = node_output.get("qa_result", {})
                                if qa_result and isinstance(qa_result, dict) and "error" not in qa_result:
                                    yield f"event: text_chunk\ndata: {json.dumps({'content': '知识检索完成...'}, ensure_ascii=False)}\n\n"

                            elif node_name == "summarize":
                                final_response = node_output.get("final_response", "")
                                if final_response:
                                    full_content = final_response
                                    # 流式输出最终回复
                                    for offset in range(0, len(full_content), 8):
                                        chunk = full_content[offset:offset + 8]
                                        yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                                knowledge_sources = node_output.get("knowledge_sources", [])
                                if knowledge_sources:
                                    yield f"event: knowledge_sources\ndata: {json.dumps({'sources': knowledge_sources}, ensure_ascii=False)}\n\n"

                    if not full_content:
                        full_content = "抱歉，无法处理您的请求。"

            except Exception as graph_error:
                logger.warning("LangGraph 多Agent 初始化失败，降级到单Agent模式: %s", graph_error)
                yield f"event: text_chunk\ndata: {json.dumps({'content': '多Agent模式初始化失败，已降级到单Agent模式...'}, ensure_ascii=False)}\n\n"

                # 降级：使用现有的 send_message_stream 逻辑
                # 这里直接调用单Agent的 chat_stream
                from app.agent.detection_agent import detection_agent

                full_content = ""
                try:
                    async for event in detection_agent.chat_stream(agent_content, history):
                        event_type = event.get("type", "")
                        if event_type == "text_chunk":
                            token_text = event.get("content", "")
                            full_content += token_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"
                        elif event_type == "error":
                            error_content = event.get("content", "") or event.get("message", "")
                            if not error_content:
                                error_content = "AI 服务暂时不可用"
                            yield f"event: error\ndata: {json.dumps({'content': error_content}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.exception("降级单Agent 也失败")
                    full_content = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
                    yield f"event: error\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(data.content) + len(full_content)) // 2)

            # 存储 AI 回复
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                agent_used="multi_agent",
                tokens_used=tokens_used if tokens_used > 0 else None,
                latency_ms=latency_ms if latency_ms > 0 else None,
            )
            db.add(assistant_msg)

            # 更新会话
            session.message_count = (session.message_count or 0) + 2
            session.last_message_at = datetime.now(timezone.utc)
            if session.message_count == 2:
                session.title = data.content[:50] if len(data.content) > 50 else data.content
            db.commit()
            db.refresh(assistant_msg)

            # 保存到 ConversationMemory
            try:
                self.conversation_memory.save_message(
                    str(user_id), str(session.id), "user", data.content
                )
                self.conversation_memory.save_message(
                    str(user_id), str(session.id), "assistant", full_content
                )
            except Exception as e:
                logger.warning("保存对话记忆失败（不影响主流程）: %s", e)

            # 发送 done 事件
            done_data = {
                "session_id": session.id,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "message_id": assistant_msg.id,
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            db.rollback()
            logger.error("多Agent SSE 流式输出错误: %s", e)
            yield f"event: error\ndata: {json.dumps({'content': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
        finally:
            db.close()


# 全局单例
chat_service = ChatService()