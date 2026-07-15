"""add password_reset_tokens table and detection progress

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── password_reset_tokens 表 ──────────────────────────────────
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False, comment='SHA256哈希后的重置令牌'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='过期时间'),
        sa.Column('used', sa.Boolean(), nullable=True, comment='是否已使用'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_password_reset_tokens_token_hash'), 'password_reset_tokens', ['token_hash'], unique=False)

    # ── detection_tasks.progress 字段（如不存在）──────────────────
    # 该字段在 P0 中已添加到模型，此处确保数据库同步
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='detection_tasks' AND column_name='progress'"
    ))
    if result.fetchone() is None:
        op.add_column('detection_tasks', sa.Column('progress', sa.Integer(), nullable=True, comment='处理进度 0-100'))


def downgrade() -> None:
    op.drop_index(op.f('ix_password_reset_tokens_token_hash'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')

    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='detection_tasks' AND column_name='progress'"
    ))
    if result.fetchone() is not None:
        op.drop_column('detection_tasks', 'progress')
