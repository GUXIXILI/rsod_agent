"""
对话服务
处理 Agent/Chat 会话和消息的 CRUD 业务逻辑
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.entity.db_models import ChatSession, ChatMessage
from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """对话服务"""

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
        """
        获取用户会话列表（分页）
        """
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
        """
        获取会话消息历史
        Raises:
            HTTPException: 会话不存在或无权访问
        """
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
    ) -> dict:
        """
        发送消息并存储（LLM 调用做成可插拔接口，初期返回固定回复）
        Returns:
            包含 user_message 和 assistant_message 的字典
        """
        session = self._get_user_session(db, session_id, user_id)

        # 存储用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=content,
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

        # AI 回复
        reply_content, tokens_used, latency_ms = self._call_llm(content, history=history)
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply_content,
            agent_used="supervisor",  # 单LLM模式下标记为supervisor
            tokens_used=tokens_used if tokens_used > 0 else None,
            latency_ms=latency_ms if latency_ms > 0 else None,
        )
        db.add(assistant_msg)

        # 更新会话信息
        session.message_count = (session.message_count or 0) + 2
        session.last_message_at = datetime.now(timezone.utc)
        # 如果是第一条消息，用内容做标题
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
                "created_at": assistant_msg.created_at,
            },
        }

    def delete_session(self, db: Session, session_id: int, user_id: int) -> bool:
        """
        删除会话（含消息级联删除）
        """
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

    def _call_llm(self, content: str, history: list = None) -> tuple:
        """
        调用 DashScope LLM（通过 langchain-openai 兼容接口）

        Args:
            content: 用户消息内容
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]

        Returns:
            tuple: (回复内容, tokens_used, latency_ms)
        """
        try:
            llm = ChatOpenAI(
                model=settings.QWEN_MODEL,
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
                temperature=0.7,
                max_tokens=2000,
            )

            # 构建消息列表
            messages = [
                SystemMessage(
                    content="你是火灾烟雾智能检测平台的AI助手，能够帮助用户进行火灾检测相关的问答、"
                    "数据查询和分析。请用中文回答。"
                )
            ]

            # 添加历史上下文（最近10条）
            if history:
                for msg in history[-10:]:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

            # 添加当前用户消息
            messages.append(HumanMessage(content=content))

            start_time = time.time()
            response = llm.invoke(messages)
            latency_ms = int((time.time() - start_time) * 1000)

            # 获取 token 用量
            tokens_used = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens", 0)

            return response.content, tokens_used, latency_ms

        except Exception as e:
            logger.error("LLM调用失败: %s", e)
            return "AI 服务暂时不可用，请稍后重试。", 0, 0


    async def send_message_stream(self, user_id: int, data, session_id: int = None):
        """
        SSE 流式发送消息（异步生成器）

        内部自行创建和管理 DB Session，避免 FastAPI Depends 提前关闭连接。

        Yields SSE 事件:
        - event: start, data: {session_id, message_id}
        - event: token, data: {content: "xxx"}
        - event: done, data: {tokens_used, latency_ms, message_id}
        - event: error, data: {message: "xxx"}
        """
        import json
        from app.database.session import SessionLocal

        db = SessionLocal()
        user_msg_id = None  # 记录用户消息 ID，便于异常时 rollback
        try:
            # 获取或创建会话
            if session_id:
                session = self._get_user_session(db, session_id, user_id)
            else:
                session = self.create_session(db, user_id)

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

            # 发送 start 事件
            yield f"event: start\ndata: {json.dumps({'session_id': session.id, 'message_id': user_msg.id}, ensure_ascii=False)}\n\n"

            # 初始化 LLM
            llm = ChatOpenAI(
                model=settings.QWEN_MODEL,
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
                temperature=0.7,
                max_tokens=2000,
            )

            # 构建消息列表
            messages = [
                SystemMessage(
                    content="你是火灾烟雾智能检测平台的AI助手，能够帮助用户进行火灾检测相关的问答、"
                    "数据查询和分析。请用中文回答。"
                )
            ]
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            messages.append(HumanMessage(content=data.content))

            # 流式输出
            full_content = ""
            start_time = time.time()
            tokens_used = 0
            last_chunk = None

            async for chunk in llm.astream(messages):
                if chunk.content:
                    full_content += chunk.content
                    yield f"event: token\ndata: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
                last_chunk = chunk

            latency_ms = int((time.time() - start_time) * 1000)

            # 尝试从最后一个 chunk 获取 token 用量，否则简单估算
            if last_chunk and hasattr(last_chunk, "usage_metadata") and last_chunk.usage_metadata:
                tokens_used = last_chunk.usage_metadata.get("total_tokens", 0)
            if tokens_used == 0 and full_content:
                tokens_used = len(full_content) // 2  # 简单估算中文字符

            # 存储 AI 回复到数据库
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                agent_used="supervisor",
                tokens_used=tokens_used if tokens_used > 0 else None,
                latency_ms=latency_ms if latency_ms > 0 else None,
            )
            db.add(assistant_msg)

            # 更新会话
            session.message_count = (session.message_count or 0) + 2
            session.last_message_at = datetime.now(timezone.utc)
            # 如果是第一条消息，用内容做标题
            if session.message_count == 2:
                session.title = data.content[:50] if len(data.content) > 50 else data.content
            db.commit()
            db.refresh(assistant_msg)

            # 发送 done 事件
            yield f"event: done\ndata: {json.dumps({'tokens_used': tokens_used, 'latency_ms': latency_ms, 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            db.rollback()
            logger.error("SSE流式输出错误: %s", e)
            yield f"event: error\ndata: {json.dumps({'message': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
        finally:
            db.close()


# 全局单例
chat_service = ChatService()
