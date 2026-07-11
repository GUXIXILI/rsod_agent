"""
检测服务模块

基于 YOLOv11 的火焰烟雾目标检测核心服务：
- 单图检测：上传图片 → 模型推理 → 标注 → 入库 → 火情判定 → 预警
- 批量检测：多张图片循环检测
- 视频检测：逐帧检测，支持跳帧
"""
import io
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionResult, DetectionScene, DetectionTask, ModelVersion
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)


class DetectionService:
    """火灾烟雾检测服务，封装 YOLOv11 模型推理全流程"""

    def __init__(self):
        self._model_cache: Dict[int, Any] = {}
        self._lock = threading.Lock()

    def detect_single(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_file: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> DetectionTask:
        """单图检测完整流程"""
        minio_client = MinIOClient()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
        original_url = None
        try:
            # 1. 上传原图到 MinIO
            original_url = minio_client.upload_bytes(image_file, object_name, f"image/{ext}")

            # 2. 加载场景默认模型
            model = self._load_model(db, scene_id)

            # 3. 执行推理
            image = Image.open(io.BytesIO(image_file))
            image_np = np.array(image)
            results = model(image_np, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)

            # 4. 绘制检测框并上传标注图
            annotated_image = results[0].plot()
            annotated_bytes = cv2.imencode(f".{ext}", annotated_image)[1].tobytes()
            annotated_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/annotated_{filename}"
            annotated_url = minio_client.upload_bytes(annotated_bytes, annotated_object_name, f"image/{ext}")

            # 5. 创建 DetectionTask 记录
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="single",
                file_name=filename,
                original_url=original_url,
                annotated_url=annotated_url,
                status="completed",
                image_width=image.width,
                image_height=image.height,
                detected_at=datetime.now(),
            )
            db.add(task)
            db.flush()

            # 6. 为每个检测目标创建 DetectionResult
            fire_count = 0
            smoke_count = 0
            fire_area_sum = 0.0
            smoke_area_sum = 0.0
            image_area = image.width * image.height

            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1
                area = w * h

                result = DetectionResult(
                    task_id=task.id,
                    class_name=cls_name,
                    confidence=conf,
                    x_min=x1,
                    y_min=y1,
                    x_max=x2,
                    y_max=y2,
                    width=w,
                    height=h,
                    area=area,
                )
                db.add(result)

                if cls_name == "fire":
                    fire_count += 1
                    fire_area_sum += area
                elif cls_name == "smoke":
                    smoke_count += 1
                    smoke_area_sum += area

            # 7. 火情等级判定
            from app.services.fire_level_service import fire_level_service
            fire_level_result = fire_level_service.judge(
                fire_count=fire_count,
                smoke_count=smoke_count,
                fire_area=fire_area_sum / image_area if image_area > 0 else 0,
                smoke_area=smoke_area_sum / image_area if image_area > 0 else 0,
            )

            # 8. 更新 task 火情字段
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = fire_count
            task.smoke_object_count = smoke_count

            db.commit()
            db.refresh(task)

            # 9. 生成火灾预警（若需要）
            from app.services.alert_service import alert_service
            alert_service.create_alert(db, task, fire_level_result)

            logger.info(
                "单图检测完成: task_id=%s, fire_level=%s, fire_count=%d, smoke_count=%d",
                task.id, task.fire_level, fire_count, smoke_count,
            )
            return task
        except Exception as e:
            logger.exception("单图检测失败: filename=%s, error=%s", filename, e)
            error_task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="single",
                file_name=filename,
                original_url=original_url,
                annotated_url=None,
                status="failed",
                error_message=str(e),
                detected_at=datetime.now(),
            )
            db.add(error_task)
            db.commit()
            db.refresh(error_task)
            return error_task

    def detect_batch(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_files: List[bytes],
        filenames: List[str],
        **kwargs,
    ) -> List[DetectionTask]:
        """批量检测：循环调用 detect_single"""
        tasks = []
        for img_bytes, fname in zip(image_files, filenames):
            try:
                task = self.detect_single(db, user_id, scene_id, img_bytes, fname, **kwargs)
                tasks.append(task)
            except Exception as e:
                logger.error("批量检测中单个图片检测失败: filename=%s, error=%s", fname, e)
        return tasks

    def detect_video(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        video_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        frame_skip: int = 5,
    ) -> DetectionTask:
        """视频检测：逐帧检测，支持跳帧"""
        # 上传视频到 MinIO
        minio_client = MinIOClient()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
        object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
        video_url = minio_client.upload_bytes(video_bytes, object_name, f"video/{ext}")

        # 加载模型
        model = self._load_model(db, scene_id)

        # 读取视频
        temp_path = Path(settings.TRAIN_OUTPUT_DIR) / "temp" / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(video_bytes)

        output_path = temp_path.parent / f"output_{filename}"
        output_url = None

        fps = 0.0
        total_frames = 0
        width = 0
        height = 0
        fire_frames: List[int] = []
        smoke_frames: List[int] = []
        total_fire_count = 0
        total_smoke_count = 0

        try:
            cap = cv2.VideoCapture(str(temp_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 创建输出视频
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_path), fourcc, fps / max(frame_skip, 1), (width, height))

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1

                if frame_idx % frame_skip != 0:
                    out.write(frame)
                    continue

                results = model(frame, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)
                annotated_frame = results[0].plot()
                out.write(annotated_frame)

                for box in results[0].boxes:
                    cls_name = model.names[int(box.cls[0])]
                    if cls_name == "fire":
                        fire_frames.append(frame_idx)
                        total_fire_count += 1
                    elif cls_name == "smoke":
                        smoke_frames.append(frame_idx)
                        total_smoke_count += 1

            cap.release()
            out.release()

            # 上传输出视频
            output_bytes = output_path.read_bytes()
            output_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/output_{filename}"
            output_url = minio_client.upload_bytes(output_bytes, output_object_name, f"video/{ext}")
        finally:
            if 'cap' in locals():
                cap.release()
            if 'out' in locals():
                out.release()
            if temp_path.exists():
                os.remove(str(temp_path))
            if output_path.exists():
                os.remove(str(output_path))

        # 火情等级判定
        from app.services.fire_level_service import fire_level_service
        fire_level_result = fire_level_service.judge(
            fire_count=total_fire_count,
            smoke_count=total_smoke_count,
            fire_area=len(fire_frames) / max(total_frames, 1),
            smoke_area=len(smoke_frames) / max(total_frames, 1),
        )

        # 创建 DetectionTask
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_type="video",
            file_name=filename,
            original_url=video_url,
            annotated_url=output_url,
            status="completed",
            image_width=width,
            image_height=height,
            video_duration=total_frames / fps if fps > 0 else 0,
            fire_level=fire_level_result["fire_level"],
            risk_level=fire_level_result["fire_level"],
            fire_area=fire_level_result["fire_area"],
            smoke_area=fire_level_result["smoke_area"],
            fire_object_count=total_fire_count,
            smoke_object_count=total_smoke_count,
            detected_at=datetime.now(),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 生成火灾预警
        from app.services.alert_service import alert_service
        alert_service.create_alert(db, task, fire_level_result)

        logger.info(
            "视频检测完成: task_id=%s, total_frames=%d, fire_frames=%d, smoke_frames=%d",
            task.id, total_frames, len(fire_frames), len(smoke_frames),
        )
        return task

    def _load_model(self, db: Session, scene_id: int):
        """加载场景默认模型（带缓存）"""
        if scene_id in self._model_cache:
            return self._model_cache[scene_id]

        from ultralytics import YOLO

        # 查找场景默认模型版本
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.scene_id == scene_id, ModelVersion.is_default == True)
            .first()
        )

        with self._lock:
            # 加锁后再次检查，避免并发重复加载
            if scene_id in self._model_cache:
                return self._model_cache[scene_id]

            if model_version and model_version.model_path:
                model = YOLO(model_version.model_path)
            else:
                # 使用 yolov11n 作为默认模型
                model = YOLO("yolov11n.pt")

            self._model_cache[scene_id] = model

        logger.info("检测模型已加载: scene_id=%s", scene_id)
        return model


# 单例
detection_service = DetectionService()