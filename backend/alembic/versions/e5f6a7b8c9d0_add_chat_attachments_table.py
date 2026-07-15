"""add chat attachments table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("attachment_uuid", sa.String(length=36), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("object_name", sa.String(length=500), nullable=False, unique=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_attachments_attachment_uuid", "chat_attachments", ["attachment_uuid"])
    op.create_index("ix_chat_attachments_user_id", "chat_attachments", ["user_id"])
    op.create_index("ix_chat_attachments_session_id", "chat_attachments", ["session_id"])
    op.create_index("ix_chat_attachments_message_id", "chat_attachments", ["message_id"])
    op.create_index("ix_chat_attachments_created_at", "chat_attachments", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_attachments")
