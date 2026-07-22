"""add request_body to operation_log and pushed_at to fire_alert

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # operation_logs 表新增 request_body 字段（脱敏请求体摘要）
    op.add_column('operation_logs', sa.Column('request_body', sa.Text(), nullable=True, comment='请求体摘要(脱敏)'))

    # fire_alerts 表新增 pushed_at 字段，push_status 枚举扩展 dispatched
    op.add_column('fire_alerts', sa.Column('pushed_at', sa.DateTime(), nullable=True, comment='推送时间'))


def downgrade() -> None:
    op.drop_column('fire_alerts', 'pushed_at')
    op.drop_column('operation_logs', 'request_body')
