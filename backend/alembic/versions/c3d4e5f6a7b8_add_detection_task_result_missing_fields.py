"""add detection task result missing fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # detection_tasks 表新增服务层已在使用的媒体文件字段
    op.add_column('detection_tasks', sa.Column('file_name', sa.String(255), nullable=True, comment='原始文件名'))
    op.add_column('detection_tasks', sa.Column('original_url', sa.String(500), nullable=True, comment='原始文件 URL'))
    op.add_column('detection_tasks', sa.Column('annotated_url', sa.String(500), nullable=True, comment='标注结果文件 URL'))
    op.add_column('detection_tasks', sa.Column('image_width', sa.Integer(), nullable=True, comment='媒体宽度（像素）'))
    op.add_column('detection_tasks', sa.Column('image_height', sa.Integer(), nullable=True, comment='媒体高度（像素）'))
    op.add_column('detection_tasks', sa.Column('video_duration', sa.Float(), nullable=True, comment='视频时长（秒），图像时为空'))
    op.add_column('detection_tasks', sa.Column('detected_at', sa.DateTime(), nullable=True, comment='检测完成时间'))
    # detection_results 表新增边界框坐标与面积字段
    op.add_column('detection_results', sa.Column('x_min', sa.Float(), nullable=True, comment='边界框左上角 x 坐标'))
    op.add_column('detection_results', sa.Column('y_min', sa.Float(), nullable=True, comment='边界框左上角 y 坐标'))
    op.add_column('detection_results', sa.Column('x_max', sa.Float(), nullable=True, comment='边界框右下角 x 坐标'))
    op.add_column('detection_results', sa.Column('y_max', sa.Float(), nullable=True, comment='边界框右下角 y 坐标'))
    op.add_column('detection_results', sa.Column('width', sa.Integer(), nullable=True, comment='边界框宽度（像素）'))
    op.add_column('detection_results', sa.Column('height', sa.Integer(), nullable=True, comment='边界框高度（像素）'))
    op.add_column('detection_results', sa.Column('area', sa.Float(), nullable=True, comment='边界框面积（像素）'))


def downgrade() -> None:
    op.drop_column('detection_results', 'area')
    op.drop_column('detection_results', 'height')
    op.drop_column('detection_results', 'width')
    op.drop_column('detection_results', 'y_max')
    op.drop_column('detection_results', 'x_max')
    op.drop_column('detection_results', 'y_min')
    op.drop_column('detection_results', 'x_min')
    op.drop_column('detection_tasks', 'detected_at')
    op.drop_column('detection_tasks', 'video_duration')
    op.drop_column('detection_tasks', 'image_height')
    op.drop_column('detection_tasks', 'image_width')
    op.drop_column('detection_tasks', 'annotated_url')
    op.drop_column('detection_tasks', 'original_url')
    op.drop_column('detection_tasks', 'file_name')
