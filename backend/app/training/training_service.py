"""
训练服务模块

封装 YOLOv11 训练全流程，包括：
- 启动训练任务（后台线程执行）
- 训练进度追踪（通过 Ultralytics 回调记录每个 epoch 指标）
- 停止训练、查询状态、获取指标
- 解析 results.csv 补充遗漏指标
"""
import csv
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionScene, TrainingMetric, TrainingTask
from app.entity.schemas import TrainingTaskCreate

logger = get_logger(__name__)


class TrainingService:
    """YOLOv11 训练服务，封装训练全流程"""

    def __init__(self):
        # 线程安全的运行中任务注册表
        self._lock = threading.Lock()
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, bool] = {}

    # ══════════════════════════════════════════════════════════════
    # 公开方法
    # ══════════════════════════════════════════════════════════════

    def start_training(
        self, db, user_id: str, task_data: TrainingTaskCreate
    ) -> TrainingTask:
        """
        启动训练任务

        1. 生成 task_uuid
        2. 查找场景获取 scene_name 和 data_yaml_path
        3. 创建 TrainingTask 数据库记录（status=pending）
        4. 为每个用户创建独立输出目录
        5. 启动后台守护线程执行 _run_training()
        6. 返回 TrainingTask 对象
        """
        # 生成唯一任务标识
        task_uuid = str(uuid.uuid4())

        # 查找场景
        scene = db.query(DetectionScene).filter(
            DetectionScene.id == task_data.scene_id
        ).first()
        if scene is None:
            raise ValueError(f"场景不存在: scene_id={task_data.scene_id}")

        scene_name = scene.name
        # 构造 data.yaml 路径（convert_voc.py 输出到 datasets/{scene_name}/yolo_dataset/data.yaml）
        data_yaml_path = str(
            Path(settings.DATASET_BASE_DIR) / scene_name / "yolo_dataset" / "data.yaml"
        )

        # 创建训练任务数据库记录
        training_task = TrainingTask(
            user_id=int(user_id),
            scene_id=task_data.scene_id,
            task_uuid=task_uuid,
            status="pending",
            model_name=task_data.model_name,
            epochs=task_data.epochs,
            img_size=task_data.img_size,
            batch_size=task_data.batch_size,
            device=task_data.device,
            optimizer=task_data.optimizer,
            lr0=task_data.lr0,
            augment_config=task_data.augment_config,
            data_yaml=data_yaml_path,
            current_epoch=0,
            progress=0,
        )
        db.add(training_task)
        db.commit()
        db.refresh(training_task)

        # 创建用户独立输出目录
        output_dir = str(
            Path(settings.TRAIN_OUTPUT_DIR) / user_id / task_uuid
        )
        os.makedirs(output_dir, exist_ok=True)

        logger.info(
            "训练任务已创建: task_uuid=%s, scene=%s, output_dir=%s",
            task_uuid,
            scene_name,
            output_dir,
        )

        # 构建训练配置
        config = {
            "epochs": task_data.epochs,
            "batch_size": task_data.batch_size,
            "img_size": task_data.img_size,
            "device": task_data.device,
            "workers": 0,  # Windows 必须设为 0
            "model_name": task_data.model_name,
            "optimizer": task_data.optimizer,
            "lr0": task_data.lr0,
            "augment_config": task_data.augment_config,
            "data_yaml_path": data_yaml_path,
            "output_dir": output_dir,
            "scene_name": scene_name,
        }

        # 启动后台守护线程执行训练
        thread = threading.Thread(
            target=self._run_training,
            args=(SessionLocal, task_uuid, config),
            daemon=True,
        )
        with self._lock:
            self._running_tasks[task_uuid] = thread
            self._stop_flags[task_uuid] = False
        thread.start()

        return training_task

    def stop_training(self, db, task_id: str):
        """
        停止训练任务

        1. 查找任务并验证权限
        2. 设置 _stop_flags[task_id] = True
        3. 更新数据库状态为 cancelled
        """
        # 通过 task_uuid 查找（task_id 参数实际为 task_uuid）
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_id
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_id={task_id}")

        # 设置停止标志
        with self._lock:
            self._stop_flags[task_id] = True

        # 更新数据库状态
        task.status = "cancelled"
        task.updated_at = datetime.now()
        db.commit()

        logger.info("训练任务已标记停止: task_uuid=%s", task_id)

    def get_training_status(self, db, task_id: str) -> dict:
        """
        获取训练状态

        返回任务基本信息 + 最新 epoch 指标
        """
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_id
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_id={task_id}")

        # 获取最新一条指标
        latest_metric = (
            db.query(TrainingMetric)
            .filter(TrainingMetric.task_id == task.id)
            .order_by(TrainingMetric.epoch.desc())
            .first()
        )

        result = {
            "id": task.id,
            "user_id": task.user_id,
            "scene_id": task.scene_id,
            "scene_name": task.scene.name if task.scene else None,
            "task_uuid": task.task_uuid,
            "status": task.status,
            "model_name": task.model_name,
            "epochs": task.epochs,
            "current_epoch": task.current_epoch,
            "progress": task.progress,
            "img_size": task.img_size,
            "batch_size": task.batch_size,
            "device": task.device,
            "dataset_size": task.dataset_size,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

        if latest_metric:
            result["latest_metric"] = {
                "epoch": latest_metric.epoch,
                "box_loss": latest_metric.box_loss,
                "cls_loss": latest_metric.cls_loss,
                "dfl_loss": latest_metric.dfl_loss,
                "precision": latest_metric.precision,
                "recall": latest_metric.recall,
                "map50": latest_metric.map50,
                "map50_95": latest_metric.map50_95,
                "lr": latest_metric.lr,
            }

        return result

    def get_training_metrics(self, db, task_id: str) -> List[TrainingMetric]:
        """
        获取所有 epoch 指标
        """
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_id
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_id={task_id}")

        metrics = (
            db.query(TrainingMetric)
            .filter(TrainingMetric.task_id == task.id)
            .order_by(TrainingMetric.epoch.asc())
            .all()
        )
        return metrics

    def get_task_list(self, db, user_id: str, limit: int = 20) -> List[TrainingTask]:
        """
        返回用户训练任务列表，按创建时间倒序
        """
        tasks = (
            db.query(TrainingTask)
            .filter(TrainingTask.user_id == int(user_id))
            .order_by(TrainingTask.created_at.desc())
            .limit(limit)
            .all()
        )
        return tasks

    def parse_results_csv(self, db, task_uuid: str) -> dict:
        """
        解析 results.csv 返回结构化数据
        """
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_uuid={task_uuid}")

        # 构建 results.csv 路径
        results_csv_path = Path(settings.TRAIN_OUTPUT_DIR) / str(task.user_id) / task_uuid / "train" / "results.csv"

        if not results_csv_path.exists():
            return {"columns": [], "rows": [], "message": "results.csv 尚未生成"}

        rows = []
        columns = []
        try:
            with open(results_csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                # 去除列名前后的空格
                columns = [col.strip() for col in next(reader)]
                for row in reader:
                    rows.append(row)
        except Exception as e:
            logger.error("解析 results.csv 失败: %s", e)
            return {"columns": columns, "rows": rows, "error": str(e)}

        return {"columns": columns, "rows": rows}

    # ══════════════════════════════════════════════════════════════
    # 内部方法
    # ══════════════════════════════════════════════════════════════

    def _run_training(self, db_session_factory, task_uuid: str, config: dict):
        """
        后台线程执行训练

        1. 使用独立数据库会话
        2. 更新状态为 running
        3. 加载预训练模型
        4. 临时修改 data.yaml 的 path 为绝对路径
        5. 注册 Ultralytics 回调 on_train_epoch_end
        6. 调用 model.train() 执行训练
        7. 训练完成后调用 _parse_final_results()
        8. 恢复 data.yaml 原始 path
        9. 更新状态为 completed/failed
        10. 清理 _running_tasks 和 _stop_flags
        """
        db = db_session_factory()
        # 在 try 外部初始化 original_path，确保 finally 块中可安全引用
        data_yaml_path = config.get("data_yaml_path")
        original_path = None
        try:
            # 更新任务状态为 running
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()
            if task is None:
                logger.error("训练任务在数据库中不存在: task_uuid=%s", task_uuid)
                return

            task.status = "running"
            task.started_at = datetime.now()
            task.updated_at = datetime.now()
            db.commit()

            logger.info("训练开始: task_uuid=%s", task_uuid)

            # 加载预训练模型
            from ultralytics import YOLO

            model_name = config.get("model_name", "yolo11n.pt")
            model = YOLO(model_name)
            logger.info("预训练模型已加载: %s", model_name)

            # 临时修改 data.yaml 的 path 为绝对路径
            if data_yaml_path and os.path.isfile(data_yaml_path):
                with open(data_yaml_path, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f)
                original_path = yaml_data.get("path")
                # 将 path 设为绝对路径，确保 Ultralytics 正确找到数据集
                yaml_data["path"] = str(
                    Path(data_yaml_path).parent.resolve()
                )
                with open(data_yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        yaml_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                logger.info(
                    "data.yaml path 已临时修改为绝对路径: %s", yaml_data["path"]
                )

            # 注册训练回调
            def on_train_epoch_end(trainer):
                """每个 epoch 结束时记录指标"""
                try:
                    # 检查停止标志
                    with self._lock:
                        if self._stop_flags.get(task_uuid, False):
                            trainer.stop_training = True
                            logger.info("训练已收到停止信号: task_uuid=%s", task_uuid)
                            return

                    # 从 trainer.metrics 读取指标
                    metrics = trainer.metrics
                    epoch = trainer.epoch + 1  # trainer.epoch 从 0 开始

                    # 创建独立数据库会话写入指标
                    metric_db = db_session_factory()
                    try:
                        task_inner = metric_db.query(TrainingTask).filter(
                            TrainingTask.task_uuid == task_uuid
                        ).first()
                        if task_inner is None:
                            return

                        # 创建 TrainingMetric 记录
                        metric = TrainingMetric(
                            task_id=task_inner.id,
                            epoch=epoch,
                            box_loss=self._safe_float(metrics.get("train/box_loss")),
                            cls_loss=self._safe_float(metrics.get("train/cls_loss")),
                            dfl_loss=self._safe_float(metrics.get("train/dfl_loss")),
                            precision=self._safe_float(
                                metrics.get("metrics/precision(B)")
                            ),
                            recall=self._safe_float(metrics.get("metrics/recall(B)")),
                            map50=self._safe_float(metrics.get("metrics/mAP50(B)")),
                            map50_95=self._safe_float(
                                metrics.get("metrics/mAP50-95(B)")
                            ),
                            lr=self._safe_float(metrics.get("lr/pg0")),
                        )
                        metric_db.add(metric)

                        # 更新 TrainingTask 的 current_epoch 和 progress
                        total_epochs = task_inner.epochs
                        task_inner.current_epoch = epoch
                        task_inner.progress = (
                            int(epoch / total_epochs * 100) if total_epochs > 0 else 0
                        )
                        task_inner.updated_at = datetime.now()
                        metric_db.commit()

                        logger.debug(
                            "Epoch %d/%d 指标已记录: task_uuid=%s",
                            epoch,
                            total_epochs,
                            task_uuid,
                        )
                    finally:
                        metric_db.close()
                except Exception:
                    logger.exception("记录训练指标异常: task_uuid=%s", task_uuid)

            model.add_callback("on_train_epoch_end", on_train_epoch_end)

            # 构建训练参数
            output_dir = config["output_dir"]
            train_args = {
                "data": data_yaml_path,
                "epochs": config.get("epochs", 100),
                "batch": config.get("batch_size", 16),
                "imgsz": config.get("img_size", 640),
                "device": config.get("device", "cpu"),
                "workers": config.get("workers", 0),
                "project": output_dir,
                "name": "train",
                "exist_ok": True,
                "pretrained": True,
                "verbose": True,
                "save": True,
                "save_period": 10,
            }

            # 执行训练
            logger.info("开始执行训练: task_uuid=%s, args=%s", task_uuid, train_args)
            model.train(**train_args)
            logger.info("训练完成: task_uuid=%s", task_uuid)

            # 训练完成后从 results.csv 补充遗漏指标
            results_dir = Path(output_dir) / "train"
            self._parse_final_results(db, task_uuid, str(results_dir))

            # 更新任务状态为 completed
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()
            if task and task.status != "cancelled":
                task.status = "completed"
                task.progress = 100
                task.completed_at = datetime.now()
                task.updated_at = datetime.now()
                db.commit()
                logger.info("训练任务状态已更新为 completed: task_uuid=%s", task_uuid)

        except Exception as e:
            logger.exception("训练失败: task_uuid=%s, error=%s", task_uuid, e)
            # 更新状态为 failed
            try:
                task = db.query(TrainingTask).filter(
                    TrainingTask.task_uuid == task_uuid
                ).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.updated_at = datetime.now()
                    db.commit()
            except Exception:
                logger.exception("更新训练失败状态异常: task_uuid=%s", task_uuid)
        finally:
            # 恢复 data.yaml 原始 path（data_yaml_path 已在 try 外定义）
            if data_yaml_path and original_path is not None and os.path.isfile(data_yaml_path):
                try:
                    with open(data_yaml_path, "r", encoding="utf-8") as f:
                        yaml_data = yaml.safe_load(f)
                    yaml_data["path"] = original_path
                    with open(data_yaml_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            yaml_data,
                            f,
                            default_flow_style=False,
                            allow_unicode=True,
                            sort_keys=False,
                        )
                    logger.info("data.yaml path 已恢复为原始值: %s", original_path)
                except Exception:
                    logger.exception("恢复 data.yaml path 失败")

            db.close()

            # 清理运行中任务注册表
            with self._lock:
                self._running_tasks.pop(task_uuid, None)
                self._stop_flags.pop(task_uuid, None)

    def _parse_final_results(self, db, task_uuid: str, results_dir: str):
        """
        解析 Ultralytics 生成的 results.csv 文件，
        将已存在的 epoch 指标补充到数据库（防止回调遗漏）
        """
        results_csv = Path(results_dir) / "results.csv"
        if not results_csv.exists():
            logger.warning("results.csv 不存在，跳过最终指标解析: %s", results_csv)
            return

        try:
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()
            if task is None:
                return

            # 获取已存在的 epoch 集合
            existing_epochs = set()
            existing_metrics = (
                db.query(TrainingMetric)
                .filter(TrainingMetric.task_id == task.id)
                .all()
            )
            for m in existing_metrics:
                existing_epochs.add(m.epoch)

            with open(results_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 去除列名中的空格
                    row = {k.strip(): v for k, v in row.items()}

                    epoch_str = row.get("epoch", "").strip()
                    if not epoch_str:
                        continue
                    try:
                        epoch = int(float(epoch_str))
                    except (ValueError, TypeError):
                        continue

                    # 跳过已存在的 epoch
                    if epoch in existing_epochs:
                        continue

                    metric = TrainingMetric(
                        task_id=task.id,
                        epoch=epoch,
                        box_loss=self._safe_float(row.get("train/box_loss")),
                        cls_loss=self._safe_float(row.get("train/cls_loss")),
                        dfl_loss=self._safe_float(row.get("train/dfl_loss")),
                        precision=self._safe_float(
                            row.get("metrics/precision(B)")
                        ),
                        recall=self._safe_float(row.get("metrics/recall(B)")),
                        map50=self._safe_float(row.get("metrics/mAP50(B)")),
                        map50_95=self._safe_float(
                            row.get("metrics/mAP50-95(B)")
                        ),
                        lr=self._safe_float(row.get("lr/pg0")),
                    )
                    db.add(metric)
                    existing_epochs.add(epoch)

            db.commit()
            logger.info(
                "最终指标解析完成: task_uuid=%s, 补充 %d 条记录",
                task_uuid,
                len(existing_epochs) - len(existing_metrics),
            )
        except Exception:
            logger.exception("解析 results.csv 失败: task_uuid=%s", task_uuid)

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """安全转换为 float，转换失败返回 None"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# 单例实例
training_service = TrainingService()