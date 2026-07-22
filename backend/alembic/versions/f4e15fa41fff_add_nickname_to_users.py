"""add_nickname_to_users

Revision ID: f4e15fa41fff
Revises: e5f6a7b8c9d0
Create Date: 2026-07-18 15:28:27.983073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4e15fa41fff'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 users 表的 nickname 列，支持用户自定义昵称"""
    op.add_column('users', sa.Column('nickname', sa.String(length=50), nullable=True, comment='昵称（用户自定义显示名）'))


def downgrade() -> None:
    """回滚：删除 nickname 列"""
    op.drop_column('users', 'nickname')