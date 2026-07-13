"""remove weather traffic hazard tables

Revision ID: a1b2c3d4e5f6
Revises: 1d6b4c9c2fcb
Create Date: 2026-07-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '1d6b4c9c2fcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除旧方向四张表
    op.drop_index(op.f('ix_hazard_alerts_location_id'), table_name='hazard_alerts')
    op.drop_table('hazard_alerts')
    op.drop_index(op.f('ix_road_hazard_predictions_location_id'), table_name='road_hazard_predictions')
    op.drop_table('road_hazard_predictions')
    op.drop_index(op.f('ix_traffic_data_location_id'), table_name='traffic_data')
    op.drop_table('traffic_data')
    op.drop_index(op.f('ix_weather_data_location_id'), table_name='weather_data')
    op.drop_table('weather_data')
    # 删除 DetectionScene 交通字段
    op.drop_column('detection_scenes', 'monitoring_type')
    op.drop_column('detection_scenes', 'road_id')
    op.drop_column('detection_scenes', 'longitude')
    op.drop_column('detection_scenes', 'latitude')
    # 删除 TrainingTask.model_type
    op.drop_column('training_tasks', 'model_type')


def downgrade() -> None:
    # 旧方向不再使用，不提供 downgrade
    pass