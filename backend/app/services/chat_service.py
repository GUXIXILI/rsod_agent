"""
对话服务
处理 Agent/Chat 会话和消息的 CRUD 业务逻辑
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

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

    @staticmethod
    def _build_stub_reply(content: str, history: list = None) -> str:
        """根据输入生成确定性的本地占位回复，不访问任何外部大模型服务。"""
        normalized = content.strip()
        if any(keyword in normalized for keyword in ("火", "烟", "告警", "检测")):
            return (
                "这是本地占位回复：已收到火灾烟雾检测相关问题。"
                "当前版本未连接真实大模型服务，请结合检测结果和人工复核进行处理。"
            )
        history_hint = "，并已读取最近的会话上下文" if history else ""
        return (
            f"这是本地占位回复：已收到你的消息“{normalized[:50]}”{history_hint}。"
            "当前版本未连接真实大模型服务。"
        )

    def _call_llm(self, content: str, history: list = None) -> tuple:
        """
        使用本地占位实现生成回复。

        参数:
            content: 用户消息内容
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]

        返回:
            tuple: (回复内容, 估算 token 数, 延迟毫秒数)
        """
        start_time = time.time()
        reply = self._build_stub_reply(content, history)
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = max(1, (len(content) + len(reply)) // 2)
        return reply, tokens_used, latency_ms


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

            # 占位回复按固定长度切片，保持 SSE 接口的流式事件契约。
            full_content = self._build_stub_reply(data.content, history)
            start_time = time.time()
            for offset in range(0, len(full_content), 8):
                chunk = full_content[offset : offset + 8]
                yield f"event: token\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(data.content) + len(full_content)) // 2)

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
