"""add fire detection fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DetectionScene 新增火灾监控点字段
    op.add_column('detection_scenes', sa.Column('location_type', sa.String(50), nullable=True, comment='监控点类型：warehouse/forest/factory/building/site'))
    op.add_column('detection_scenes', sa.Column('address', sa.String(500), nullable=True, comment='监控点详细地址'))
    op.add_column('detection_scenes', sa.Column('camera_count', sa.Integer(), nullable=True, comment='摄像头数量'))
    # DetectionTask 新增火情判定字段
    op.add_column('detection_tasks', sa.Column('fire_level', sa.String(20), nullable=True, comment='火情等级：safe/notice/warning/danger'))
    op.add_column('detection_tasks', sa.Column('fire_area', sa.Float(), nullable=True, comment='火焰面积占比'))
    op.add_column('detection_tasks', sa.Column('smoke_area', sa.Float(), nullable=True, comment='烟雾面积占比'))
    op.add_column('detection_tasks', sa.Column('fire_object_count', sa.Integer(), nullable=True, comment='火焰目标数'))
    op.add_column('detection_tasks', sa.Column('smoke_object_count', sa.Integer(), nullable=True, comment='烟雾目标数'))
    # 新建 fire_alerts 表
    op.create_table('fire_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('detection_tasks.id'), nullable=False, comment='关联检测任务'),
        sa.Column('scene_id', sa.Integer(), sa.ForeignKey('detection_scenes.id'), nullable=False, comment='监控点'),
        sa.Column('fire_level', sa.String(20), nullable=False, comment='火情等级：notice/warning/danger'),
        sa.Column('content', sa.Text(), nullable=False, comment='预警内容'),
        sa.Column('suggestion', sa.Text(), nullable=True, comment='处置建议'),
        sa.Column('channels', sa.JSON(), nullable=True, comment='推送渠道'),
        sa.Column('push_status', sa.String(20), nullable=True, comment='推送状态：pending/sent/failed'),
        sa.Column('handled_status', sa.String(20), nullable=True, comment='处理状态：unhandled/handling/resolved'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('handled_at', sa.DateTime(), nullable=True, comment='处理时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fire_alerts_task_id'), 'fire_alerts', ['task_id'], unique=False)
    op.create_index(op.f('ix_fire_alerts_scene_id'), 'fire_alerts', ['scene_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fire_alerts_scene_id'), table_name='fire_alerts')
    op.drop_index(op.f('ix_fire_alerts_task_id'), table_name='fire_alerts')
    op.drop_table('fire_alerts')
    op.drop_column('detection_tasks', 'smoke_object_count')
    op.drop_column('detection_tasks', 'fire_object_count')
    op.drop_column('detection_tasks', 'smoke_area')
    op.drop_column('detection_tasks', 'fire_area')
    op.drop_column('detection_tasks', 'fire_level')
    op.drop_column('detection_scenes', 'camera_count')
    op.drop_column('detection_scenes', 'address')
    op.drop_column('detection_scenes', 'location_type')