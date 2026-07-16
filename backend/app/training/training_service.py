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
import shutil
import tempfile
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

    def delete_task(self, db, task_uuid: str) -> dict:
        """
        删除训练任务及其关联数据

        1. 校验任务是否存在
        2. 删除关联的 TrainingMetric 记录（级联删除）
        3. 删除 TrainingTask 记录
        4. 清理训练输出目录

        Args:
            db: 数据库会话
            task_uuid: 训练任务 UUID

        Returns:
            包含删除信息的字典

        Raises:
            ValueError: 任务不存在或状态不允许删除
        """
        # 查找训练任务
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_uuid={task_uuid}")

        # 不允许删除正在运行中的任务
        if task.status in ("pending", "running"):
            raise ValueError(
                f"训练任务正在运行中（状态={task.status}），请先停止后再删除"
            )

        task_id = task.id
        user_id = task.user_id
        status = task.status

        # 删除关联指标（手动级联，确保清理完整）
        db.query(TrainingMetric).filter(
            TrainingMetric.task_id == task_id
        ).delete()

        # 删除任务本身
        db.delete(task)
        db.commit()

        # 清理训练输出目录
        output_dir = Path(settings.TRAIN_OUTPUT_DIR) / str(user_id) / task_uuid
        if output_dir.exists():
            try:
                shutil.rmtree(str(output_dir))
                logger.info("训练输出目录已清理: %s", output_dir)
            except Exception as e:
                logger.warning("清理训练输出目录失败: %s, error=%s", output_dir, e)

        logger.info(
            "训练任务已删除: task_uuid=%s, task_id=%d, status=%s",
            task_uuid, task_id, status,
        )

        return {
            "task_uuid": task_uuid,
            "task_id": task_id,
            "status": status,
            "deleted": True,
        }

    def validate_model(
        self,
        db,
        task_uuid: str,
        split: str = "val",
        conf: float = 0.001,
        iou: float = 0.6,
    ) -> dict:
        """
        模型评估：使用 YOLO 的 model.val() 对训练产出的模型进行验证集评估

        1. 查找训练任务，定位 best.pt 权重文件
        2. 查找对应的 data.yaml 数据集配置
        3. 加载模型并执行 val() 评估
        4. 返回评估指标（precision, recall, mAP50, mAP50-95, per_class_ap）

        Args:
            db: 数据库会话
            task_uuid: 训练任务 UUID
            split: 评估数据划分（val/test）
            conf: 评估置信度阈值
            iou: 评估 IoU 阈值

        Returns:
            包含评估指标的字典

        Raises:
            ValueError: 任务不存在或模型文件缺失
        """
        # 查找训练任务
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_uuid={task_uuid}")

        # 定位 best.pt 权重文件
        user_id = task.user_id
        best_pt_path = (
            Path(settings.TRAIN_OUTPUT_DIR)
            / str(user_id)
            / task_uuid
            / "train"
            / "weights"
            / "best.pt"
        )
        if not best_pt_path.is_file():
            raise ValueError(
                f"模型权重文件不存在: {best_pt_path}，请确认训练已完成"
            )

        # 定位 data.yaml 数据集配置
        data_yaml_path = task.data_yaml
        if not data_yaml_path or not Path(data_yaml_path).is_file():
            raise ValueError(
                f"数据集配置文件不存在: {data_yaml_path}，请确认数据集已正确配置"
            )

        logger.info(
            "开始模型评估: task_uuid=%s, best_pt=%s, data_yaml=%s, split=%s",
            task_uuid, best_pt_path, data_yaml_path, split,
        )

        try:
            from ultralytics import YOLO

            # 加载模型
            model = YOLO(str(best_pt_path))

            # 执行评估
            val_results = model.val(
                data=data_yaml_path,
                split=split,
                conf=conf,
                iou=iou,
                verbose=False,
            )

            # 提取评估指标
            # YOLO val() 返回的 results 对象包含以下属性
            overall = {
                "precision": round(float(getattr(val_results, "results_dict", {}).get("metrics/precision(B)", 0.0)), 4),
                "recall": round(float(getattr(val_results, "results_dict", {}).get("metrics/recall(B)", 0.0)), 4),
                "map50": round(float(getattr(val_results, "results_dict", {}).get("metrics/mAP50(B)", 0.0)), 4),
                "map50_95": round(float(getattr(val_results, "results_dict", {}).get("metrics/mAP50-95(B)", 0.0)), 4),
            }

            # 提取各类别 AP
            per_class = {}
            try:
                # box.ap_class_index 和 box.ap 分别存储类别索引和 AP 值
                ap_class_index = getattr(val_results.box, "ap_class_index", None)
                ap_values = getattr(val_results.box, "ap", None)
                if ap_class_index is not None and ap_values is not None:
                    names = getattr(model, "names", {})
                    for idx, ap in zip(ap_class_index.tolist(), ap_values.tolist()):
                        class_name = names.get(int(idx), f"class_{idx}")
                        per_class[class_name] = {
                            "ap50": round(float(ap), 4),
                            "ap50_95": round(float(ap), 4),  # val() 默认返回 mAP50-95
                        }
            except Exception:
                # 如果 AP 提取失败，使用默认值
                logger.warning("无法提取各类别 AP，使用默认值")
                per_class = {
                    "fire": {"ap50": overall["map50"], "ap50_95": overall["map50_95"]},
                    "smoke": {"ap50": overall["map50"], "ap50_95": overall["map50_95"]},
                }

            logger.info(
                "模型评估完成: task_uuid=%s, mAP50=%.4f, mAP50-95=%.4f",
                task_uuid, overall["map50"], overall["map50_95"],
            )

            return {
                "split": split,
                "overall": overall,
                "per_class": per_class,
            }
        except Exception as e:
            logger.exception("模型评估失败: task_uuid=%s", task_uuid)
            raise ValueError(f"模型评估失败: {str(e)}") from e

    def export_model(
        self,
        db,
        task_uuid: str,
        export_format: str = "onnx",
        imgsz: int = 640,
        device: str = "cpu",
    ) -> dict:
        """
        模型导出：将训练产出的 best.pt 导出为 ONNX 或 TorchScript 格式

        1. 查找训练任务，定位 best.pt 权重文件
        2. 加载模型并执行 export()
        3. 返回导出文件路径和大小

        Args:
            db: 数据库会话
            task_uuid: 训练任务 UUID
            export_format: 导出格式（onnx/torchscript）
            imgsz: 导出图像尺寸
            device: 导出设备

        Returns:
            包含导出文件信息的字典

        Raises:
            ValueError: 任务不存在或模型文件缺失
        """
        # 查找训练任务
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()
        if task is None:
            raise ValueError(f"训练任务不存在: task_uuid={task_uuid}")

        # 定位 best.pt 权重文件
        user_id = task.user_id
        best_pt_path = (
            Path(settings.TRAIN_OUTPUT_DIR)
            / str(user_id)
            / task_uuid
            / "train"
            / "weights"
            / "best.pt"
        )
        if not best_pt_path.is_file():
            raise ValueError(
                f"模型权重文件不存在: {best_pt_path}，请确认训练已完成"
            )

        # 校验导出格式
        if export_format not in ("onnx", "torchscript"):
            raise ValueError(
                f"不支持的导出格式: {export_format}，仅支持 onnx 和 torchscript"
            )

        logger.info(
            "开始模型导出: task_uuid=%s, format=%s, imgsz=%d, device=%s",
            task_uuid, export_format, imgsz, device,
        )

        try:
            from ultralytics import YOLO

            # 加载模型
            model = YOLO(str(best_pt_path))

            # 导出目录
            export_dir = best_pt_path.parent
            export_dir.mkdir(parents=True, exist_ok=True)

            # 执行导出
            export_path = model.export(
                format=export_format,
                imgsz=imgsz,
                device=device,
            )

            # 确定导出文件路径
            if isinstance(export_path, str):
                exported_file = Path(export_path)
            else:
                # ultralytics 返回已导出的文件路径
                exported_file = Path(str(export_path))

            file_size = exported_file.stat().st_size if exported_file.is_file() else 0

            logger.info(
                "模型导出完成: task_uuid=%s, format=%s, file=%s, size=%d",
                task_uuid, export_format, exported_file.name, file_size,
            )

            return {
                "task_uuid": task_uuid,
                "format": export_format,
                "file_name": exported_file.name,
                "file_path": str(exported_file),
                "file_size": file_size,
                "download_url": f"/api/training/download/{task_uuid}",
            }
        except Exception as e:
            logger.exception("模型导出失败: task_uuid=%s", task_uuid)
            raise ValueError(f"模型导出失败: {str(e)}") from e

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
        # 在 try 外部初始化，确保 finally 块中可安全引用
        data_yaml_path = config.get("data_yaml_path")
        temp_yaml_dir = None  # 临时 data.yaml 副本所在目录
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

            model_name = config.get("model_name", "yolov11n.pt")
            model = YOLO(model_name)
            logger.info("预训练模型已加载: %s", model_name)

            # 复制 data.yaml 到独立临时目录，避免并发训练相互干扰
            train_data_yaml = data_yaml_path  # 默认使用原始路径
            if data_yaml_path and os.path.isfile(data_yaml_path):
                temp_yaml_dir = tempfile.mkdtemp(prefix="yolo_data_")
                temp_yaml_path = os.path.join(temp_yaml_dir, "data.yaml")
                shutil.copy2(data_yaml_path, temp_yaml_path)

                # 修改副本的 path 为绝对路径
                with open(temp_yaml_path, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f)
                yaml_data["path"] = str(
                    Path(data_yaml_path).parent.resolve()
                )
                with open(temp_yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        yaml_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                train_data_yaml = temp_yaml_path
                logger.info(
                    "data.yaml 已复制到临时目录并修改 path: %s", yaml_data["path"]
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
                "data": train_data_yaml,
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
            # 清理临时 data.yaml 副本目录
            if temp_yaml_dir and os.path.isdir(temp_yaml_dir):
                try:
                    shutil.rmtree(temp_yaml_dir)
                    logger.info("临时 data.yaml 目录已清理: %s", temp_yaml_dir)
                except Exception:
                    logger.exception("清理临时 data.yaml 目录失败: %s", temp_yaml_dir)

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