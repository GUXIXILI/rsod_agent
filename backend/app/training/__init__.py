"""
训练模块 (Training Module)

提供数据集格式转换、数据集划分、模型训练服务等核心功能。
对外暴露 DataConverter、DatasetSplitter、TrainingService 三个核心类。
"""
from app.training.data_converter import DataConverter
from app.training.dataset_splitter import DatasetSplitter

# TrainingService 在 Day06 创建，延迟导入避免循环依赖
try:
    from app.training.training_service import TrainingService, training_service
except ImportError:
    TrainingService = None  # type: ignore
    training_service = None  # type: ignore

__all__ = ["DataConverter", "DatasetSplitter", "TrainingService", "training_service"]