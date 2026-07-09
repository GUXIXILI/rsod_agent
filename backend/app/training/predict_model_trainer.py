"""
预测模型训练器模块

封装 XGBoost / LSTM 预测模型训练全流程：
- 从 WeatherData / TrafficData / hazard 标签构建训练集
- 训练 XGBoost 分类器或 LSTM 时序预测模型
- 保存模型到 runs/train/{user_id}/{task_uuid}/
- 记录训练指标到 TrainingMetric 表
"""
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import TrainingMetric, TrainingTask

logger = get_logger(__name__)


class PredictModelTrainer:
    """预测模型训练器，支持 XGBoost 和 LSTM 训练"""

    def __init__(self):
        self._stop_flags: Dict[str, bool] = {}

    def train(
        self,
        db_session_factory,
        task_uuid: str,
        config: Dict[str, Any],
    ):
        """
        启动预测模型训练（后台线程）

        根据 model_type 路由到具体训练器：
        - xgboost: 训练 XGBoost 分类器
        - lstm: 训练 LSTM 时序预测模型
        """
        # 训练在后台线程执行，避免阻塞 API 响应
        thread = threading.Thread(
            target=self._run_training,
            args=(db_session_factory, task_uuid, config),
            daemon=True,
        )
        self._stop_flags[task_uuid] = False
        thread.start()

    def _run_training(
        self, db_session_factory, task_uuid: str, config: Dict[str, Any]
    ):
        """
        后台线程执行训练

        流程：构建数据集 → 训练模型 → 保存模型 → 记录指标 → 更新状态
        """
        db = db_session_factory()
        try:
            # 更新任务状态为 running
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()
            if task is None:
                logger.error("训练任务不存在: task_uuid=%s", task_uuid)
                return

            task.status = "running"
            task.started_at = datetime.now()
            task.updated_at = datetime.now()
            db.commit()

            model_type = config.get("model_type", "xgboost")
            logger.info(
                "预测模型训练开始: task_uuid=%s, model_type=%s",
                task_uuid,
                model_type,
            )

            # 创建输出目录
            output_dir = Path(settings.TRAIN_OUTPUT_DIR) / str(task.user_id) / task_uuid
            os.makedirs(output_dir, exist_ok=True)

            # 构建训练集
            X, y = self._build_dataset(db, config)

            if len(X) == 0:
                raise ValueError("训练集为空，请确保有足够的数据")

            # 根据模型类型训练
            if model_type == "xgboost":
                model_path = self._train_xgboost(X, y, output_dir, task_uuid, db, task)
            elif model_type == "lstm":
                model_path = self._train_lstm(X, y, output_dir, task_uuid, db, task)
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")

            # 更新任务状态为完成
            task.status = "completed"
            task.completed_at = datetime.now()
            task.updated_at = datetime.now()
            db.commit()

            logger.info(
                "预测模型训练完成: task_uuid=%s, model_path=%s",
                task_uuid,
                model_path,
            )

        except Exception as e:
            logger.exception("预测模型训练失败: task_uuid=%s", task_uuid)
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()
            if task:
                task.status = "failed"
                task.error_message = str(e)
                task.updated_at = datetime.now()
                db.commit()
        finally:
            db.close()
            self._stop_flags.pop(task_uuid, None)

    def _build_dataset(self, db, config: Dict[str, Any]):
        """
        构建训练数据集（占位，后续从数据表构建）

        当前返回空列表，待有人完成数据采集后实现。
        训练集构建逻辑：
        1. 从 WeatherData 和 TrafficData 提取特征
        2. 从 RoadHazardPrediction 或人工标注获取标签
        3. 拼接为 (X, y) 返回
        """
        logger.info("数据集构建待实现，返回空数据")
        # 返回空列表表示训练数据尚未就绪
        return [], []

    def _train_xgboost(
        self, X, y, output_dir: Path, task_uuid: str, db, task: TrainingTask
    ) -> str:
        """
        训练 XGBoost 分类器

        使用 sklearn 的 train_test_split 划分训练/验证集，
        训练 XGBoost 多分类器，记录指标到 TrainingMetric 表。
        """
        try:
            import numpy as np
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
        except ImportError as e:
            raise ImportError(
                f"缺少依赖: {e}。请运行 pip install xgboost scikit-learn"
            )

        X = np.array(X)
        y = np.array(y)

        # 划分训练集和验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # 训练 XGBoost
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective="multi:softprob",
            random_state=42,
        )
        model.fit(X_train, y_train)

        # 评估
        y_pred = model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)

        # 保存模型
        model_path = str(output_dir / "xgboost_model.json")
        model.save_model(model_path)

        # 记录训练指标
        metric = TrainingMetric(
            task_id=task.id,
            epoch=1,
            box_loss=0.0,  # 预测模型不使用这些指标
            cls_loss=0.0,
            dfl_loss=0.0,
            precision=accuracy,
            recall=accuracy,
            map50=accuracy,
            map50_95=accuracy,
            lr=0.1,
        )
        db.add(metric)
        task.current_epoch = 1
        task.progress = 100
        db.commit()

        logger.info(
            "XGBoost 训练完成: accuracy=%.4f, model_path=%s",
            accuracy,
            model_path,
        )

        return model_path

    def _train_lstm(
        self, X, y, output_dir: Path, task_uuid: str, db, task: TrainingTask
    ) -> str:
        """
        训练 LSTM 时序预测模型（占位，后续实现）

        LSTM 需要时序数据，当前仅记录日志并抛出异常提示。
        后续实现时需：
        1. 按时间窗口构建序列数据
        2. 定义 LSTM 网络结构
        3. 训练并保存模型
        """
        logger.warning("LSTM 训练尚未实现，请使用 XGBoost 或后续补充")
        raise NotImplementedError("LSTM 训练器尚未实现，请使用 XGBoost")


# 全局单例
predict_model_trainer = PredictModelTrainer()