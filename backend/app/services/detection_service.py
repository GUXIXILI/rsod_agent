"""
检测服务模块

基于 YOLOv11 的火焰烟雾目标检测核心服务：
- 单图检测：上传图片 → 模型推理 → 标注 → 入库 → 火情判定 → 预警
- 批量检测：多张图片循环检测
- 视频检测：逐帧检测，支持跳帧
"""
import base64
import io
import json
import os
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch
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

    MAX_CACHE_SIZE = 4

    # ══════════════════════════════════════════════════════════════
    # 过度识别兜底常量（避免单图检测出 300+ 目标导致标注图过大）
    # ══════════════════════════════════════════════════════════════
    MAX_DETECTIONS_PER_IMAGE = 50     # 单图最多保留的检测框数量
    MIN_CONFIDENCE = 0.15             # 最终置信度兜底（低于此值直接丢弃）
    MIN_BOX_AREA_RATIO = 0.0001       # 框面积占图像比例下限（过滤噪声框）

    def __init__(self):
        self._model_cache: OrderedDict[int, Any] = OrderedDict()
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
        # 0. 校验 scene_id 是否存在（避免外键约束违反导致 500 错误）
        scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            raise ValueError(f"场景不存在 (scene_id={scene_id})")
        minio_client = MinIOClient()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
        original_url = None
        # 1. 上传原图到 MinIO（非致命：上传失败不影响检测）
        try:
            original_url = minio_client.upload_bytes(image_file, object_name, f"image/{ext}")
        except Exception as upload_err:
            logger.warning("MinIO 原图上传失败，跳过存储继续检测: %s", upload_err)
            # 兜底：保存到本地 static/originals/ 目录
            try:
                _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
                local_originals_dir = _BACKEND_ROOT / "static" / "originals"
                local_originals_dir.mkdir(parents=True, exist_ok=True)
                local_path = local_originals_dir / filename
                local_path.write_bytes(image_file)
                original_url = f"/static/originals/{filename}"
                logger.info("原图已保存到本地兜底路径: %s", original_url)
            except Exception as local_err:
                logger.warning("本地原图兜底保存也失败: %s", local_err)

        try:
            # 2. 加载场景默认模型
            model = self._load_model(db, scene_id)

            # 3. 执行推理（强制转为 RGB 避免 RGBA 四通道导致模型报错）
            # 注意：必须传 PIL Image 而非 numpy 数组，因为 YOLO 对 PIL Image 和 numpy
            # 数组的预处理路径不同，numpy 数组会导致检测结果全部为 0（P0 级 bug）
            image = Image.open(io.BytesIO(image_file)).convert("RGB")
            t_start = datetime.now()
            results = model(image, conf=conf_threshold, iou=iou_threshold, imgsz=image_size, verbose=False)
            # 记录推理耗时（优先使用 YOLO speed 指标，兜底用 wall-clock 时间）
            inference_time = (
                results[0].speed.get("inference", 0) if hasattr(results[0], "speed") and results[0].speed
                else (datetime.now() - t_start).total_seconds() * 1000
            )

            # 4. 收集并过滤检测框（避免过度识别导致 300+ 目标）
            image_area = image.width * image.height
            raw_boxes = list(results[0].boxes)

            # 按置信度从高到低排序
            raw_boxes.sort(key=lambda b: float(b.conf[0]), reverse=True)

            # 数量上限过滤：只保留置信度最高的前 N 个框
            if len(raw_boxes) > self.MAX_DETECTIONS_PER_IMAGE:
                logger.warning(
                    "检测到 %d 个目标，超过上限 %d，只保留置信度最高的 %d 个",
                    len(raw_boxes), self.MAX_DETECTIONS_PER_IMAGE, self.MAX_DETECTIONS_PER_IMAGE,
                )
                raw_boxes = raw_boxes[:self.MAX_DETECTIONS_PER_IMAGE]

            # 逐框过滤：丢弃极低置信度和过小的噪声框
            valid_boxes = []
            filtered_low_conf = 0
            filtered_tiny = 0
            for box in raw_boxes:
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1
                area = w * h
                area_ratio = area / image_area if image_area > 0 else 0

                if conf < self.MIN_CONFIDENCE:
                    filtered_low_conf += 1
                    continue
                if area_ratio < self.MIN_BOX_AREA_RATIO:
                    filtered_tiny += 1
                    continue

                valid_boxes.append((box, conf, xyxy, x1, y1, x2, y2, w, h, area))

            if filtered_low_conf > 0 or filtered_tiny > 0:
                logger.warning(
                    "过滤了 %d 个低置信度框（<%.2f）和 %d 个过小框（<%.4f%%），保留 %d 个有效框",
                    filtered_low_conf, self.MIN_CONFIDENCE,
                    filtered_tiny, self.MIN_BOX_AREA_RATIO * 100,
                    len(valid_boxes),
                )

            # 4.5 绘制标注图（只绘制过滤后保留的有效框）
            annotated_image = results[0].plot()  # 原始所有框
            if filtered_low_conf > 0 or filtered_tiny > 0 or len(raw_boxes) < len(results[0].boxes):
                # 有过滤时，在原始图上手动重新绘制，只画有效框
                annotated_image = cv2.cvtColor(
                    np.array(Image.open(io.BytesIO(image_file)).convert("RGB")), cv2.COLOR_RGB2BGR
                )
                for box_data in valid_boxes:
                    _, conf, _, x1, y1, x2, y2, _, _, _ = box_data
                    cls_id = int(box_data[0].cls[0])
                    cls_name = model.names[cls_id]
                    color = (0, 0, 255) if cls_name == "fire" else (0, 255, 255)  # 红/黄
                    cv2.rectangle(annotated_image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    label = f"{cls_name} {conf:.2f}"
                    cv2.putText(annotated_image, label, (int(x1), int(y1) - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            annotated_bytes = cv2.imencode(f".{ext}", annotated_image)[1].tobytes()
            annotated_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/annotated_{filename}"
            annotated_url = None
            try:
                annotated_url = minio_client.upload_bytes(annotated_bytes, annotated_object_name, f"image/{ext}")
            except Exception as upload_err:
                logger.warning("MinIO 标注图上传失败，跳过存储: %s", upload_err)
                # 兜底：保存到本地 static/annotated/ 目录
                try:
                    _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
                    local_annotated_dir = _BACKEND_ROOT / "static" / "annotated"
                    local_annotated_dir.mkdir(parents=True, exist_ok=True)
                    annotated_filename = f"annotated_{filename}"
                    local_annotated_path = local_annotated_dir / annotated_filename
                    local_annotated_path.write_bytes(annotated_bytes)
                    annotated_url = f"/static/annotated/{annotated_filename}"
                    logger.info("标注图已保存到本地兜底路径: %s", annotated_url)
                except Exception as local_err:
                    logger.warning("本地标注图兜底保存也失败: %s", local_err)

            # 5. 创建 DetectionTask 记录
            # 同时把标注图以 base64 形式附在对象上，供上层（如对话工具）在 MinIO
            # 上传失败时直接嵌入到回复中，避免丢失可视化结果。
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
                total_inference_time=inference_time,
            )
            task.annotated_image_base64 = base64.b64encode(annotated_bytes).decode("utf-8")
            db.add(task)
            db.flush()

            # 6. 为每个过滤后的有效检测目标创建 DetectionResult
            fire_count = 0
            smoke_count = 0
            fire_area_sum = 0.0
            smoke_area_sum = 0.0
            fire_conf_sum = 0.0
            smoke_conf_sum = 0.0

            for box_data in valid_boxes:
                box, conf, xyxy, x1, y1, x2, y2, w, h, area = box_data
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]

                result = DetectionResult(
                    task_id=task.id,
                    image_path=original_url or object_name,
                    annotated_image_url=annotated_url,
                    class_name=cls_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=xyxy,
                    x_min=x1,
                    y_min=y1,
                    x_max=x2,
                    y_max=y2,
                    width=w,
                    height=h,
                    area=area,
                    image_width=image.width,
                    image_height=image.height,
                )
                db.add(result)

                if cls_name == "fire":
                    fire_count += 1
                    fire_area_sum += area
                    fire_conf_sum += conf
                elif cls_name == "smoke":
                    smoke_count += 1
                    smoke_area_sum += area
                    smoke_conf_sum += conf

            # 7. 火情等级判定（传入平均置信度，避免低置信度误报触发预警）
            from app.services.fire_level_service import fire_level_service
            avg_fire_conf = fire_conf_sum / fire_count if fire_count > 0 else 0.0
            avg_smoke_conf = smoke_conf_sum / smoke_count if smoke_count > 0 else 0.0
            fire_level_result = fire_level_service.judge(
                fire_count=fire_count,
                smoke_count=smoke_count,
                fire_area=fire_area_sum / image_area if image_area > 0 else 0,
                smoke_area=smoke_area_sum / image_area if image_area > 0 else 0,
                avg_fire_confidence=avg_fire_conf,
                avg_smoke_confidence=avg_smoke_conf,
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
            # 回滚之前 flush 的半成品数据
            try:
                db.rollback()
            except Exception:
                pass
            # 尝试清理已上传的 MinIO 原图
            if original_url:
                try:
                    minio_client.delete_file(object_name)
                except Exception:
                    logger.warning("清理 MinIO 孤儿文件失败: %s", object_name)
            # 在新事务中创建 failed 状态记录
            try:
                error_task = DetectionTask(
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    file_name=filename,
                    original_url=None,
                    annotated_url=None,
                    status="failed",
                    error_message=str(e),
                    detected_at=datetime.now(),
                )
                db.add(error_task)
                db.commit()
                db.refresh(error_task)
                return error_task
            except Exception:
                logger.exception("创建失败任务记录也失败: filename=%s", filename)
                db.rollback()
                raise

    def detect_batch(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_files: List[bytes],
        filenames: List[str],
        **kwargs,
    ) -> List[DetectionTask]:
        """批量检测：使用线程池并发处理多张图片"""
        # 0. 校验 scene_id 是否存在（避免外键约束违反导致 500 错误）
        scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            raise ValueError(f"场景不存在 (scene_id={scene_id})")
        tasks: List[DetectionTask] = []

        def _detect_one(img_bytes: bytes, fname: str) -> Optional[DetectionTask]:
            """在独立线程中执行单图检测，使用独立 db session"""
            thread_db = SessionLocal()
            try:
                return self.detect_single(
                    thread_db, user_id, scene_id, img_bytes, fname, **kwargs
                )
            except Exception as exc:
                logger.error("批量检测中单个图片检测失败: filename=%s, error=%s", fname, exc)
                thread_db.rollback()
                return None
            finally:
                thread_db.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_detect_one, img_bytes, fname)
                for img_bytes, fname in zip(image_files, filenames)
            ]
            for f in futures:
                result = f.result()
                if result is not None:
                    tasks.append(result)
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
        progress_task_id: Optional[int] = None,
    ) -> DetectionTask:
        """视频检测：逐帧检测，支持跳帧

        注意：此方法可能在 asyncio.to_thread 中运行，
        因此创建独立的 db session 以避免跨线程共享。
        """
        # 创建独立 session（线程安全）
        own_db = SessionLocal()
        try:
            minio_client = MinIOClient()
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
            object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
            # 上传视频到 MinIO
            video_url = minio_client.upload_bytes(video_bytes, object_name, f"video/{ext}")

            # 加载模型
            model = self._load_model(own_db, scene_id)

            # 读取视频
            temp_path = Path(settings.TRAIN_OUTPUT_DIR) / "temp" / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(video_bytes)

            output_path = temp_path.parent / f"output_{filename}"
            output_url = None

            # 先创建任务记录（status=processing），以便 Redis 进度追踪可使用 task.id
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="video",
                file_name=filename,
                original_url=video_url,
                annotated_url=None,
                status="processing",
                progress=0,
                detected_at=datetime.now(),
            )
            own_db.add(task)
            own_db.commit()
            own_db.refresh(task)

            # 进度追踪关联：当外部传入 progress_task_id 时，使用它作为进度键
            owner_task_id = progress_task_id or task.id
            if owner_task_id != task.id:
                owner_task = own_db.query(DetectionTask).filter(
                    DetectionTask.id == owner_task_id
                ).first()
                if owner_task is not None:
                    owner_task.progress = 0
                    own_db.commit()

            fps = 0.0
            total_frames = 0
            width = 0
            height = 0
            fire_frames: List[int] = []
            smoke_frames: List[int] = []
            total_fire_count = 0
            total_smoke_count = 0
            last_persisted_progress = -1  # 数据库进度持久化阈值追踪

            try:
                cap = cv2.VideoCapture(str(temp_path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # 初始化 Redis 进度追踪
                try:
                    import redis as redis_lib
                    redis_client = redis_lib.Redis(
                        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                        db=settings.REDIS_DB, decode_responses=True,
                    )
                    redis_client.set(
                        f"video:progress:{owner_task_id}",
                        json.dumps({"progress": 0, "current_frame": 0, "total_frames": total_frames}),
                        ex=3600,
                    )
                except Exception:
                    redis_client = None

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

                    results = model(frame, conf=conf_threshold, iou=iou_threshold, imgsz=image_size, verbose=False)
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

                    # 更新 Redis 进度
                    current_frame = frame_idx
                    progress = int((current_frame / max(total_frames, 1)) * 100)
                    if redis_client:
                        try:
                            redis_client.set(
                                f"video:progress:{owner_task_id}",
                                json.dumps({
                                    "progress": progress,
                                    "current_frame": current_frame,
                                    "total_frames": total_frames,
                                }),
                                ex=3600,
                            )
                        except Exception:
                            pass

                    # 每 5% 增量持久化进度到数据库（Redis 缺失或进程重启后可从 DB 回退）
                    if progress >= last_persisted_progress + 5:
                        task.progress = progress
                        if owner_task_id != task.id:
                            owner_task = own_db.query(DetectionTask).filter(
                                DetectionTask.id == owner_task_id
                            ).first()
                            if owner_task is not None:
                                owner_task.progress = progress
                        own_db.commit()
                        last_persisted_progress = progress

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

            # 更新任务为已完成状态
            task.annotated_url = output_url
            task.status = "completed"
            task.progress = 100
            task.image_width = width
            task.image_height = height
            task.video_duration = total_frames / fps if fps > 0 else 0
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = total_fire_count
            task.smoke_object_count = total_smoke_count
            # 同步 owner_task 的进度为 100
            if owner_task_id != task.id:
                owner_task = own_db.query(DetectionTask).filter(
                    DetectionTask.id == owner_task_id
                ).first()
                if owner_task is not None:
                    owner_task.progress = 100
            own_db.commit()
            own_db.refresh(task)

            # 清理 Redis 进度 key
            if redis_client:
                try:
                    redis_client.delete(f"video:progress:{owner_task_id}")
                except Exception:
                    pass

            # 生成火灾预警
            from app.services.alert_service import alert_service
            alert_service.create_alert(own_db, task, fire_level_result)

            logger.info(
                "视频检测完成: task_id=%s, total_frames=%d, fire_frames=%d, smoke_frames=%d",
                task.id, total_frames, len(fire_frames), len(smoke_frames),
            )
            return task
        except Exception as error:
            # 视频检测失败：将 task 和 owner_task 状态置为 failed，写入错误信息
            if "task" in locals():
                try:
                    task.status = "failed"
                    task.error_message = str(error)
                    task.completed_at = datetime.now()
                    if "owner_task_id" in locals() and owner_task_id != task.id:
                        owner_task = own_db.query(DetectionTask).filter(
                            DetectionTask.id == owner_task_id
                        ).first()
                        if owner_task is not None:
                            owner_task.status = "failed"
                            owner_task.error_message = str(error)
                            owner_task.completed_at = datetime.now()
                    own_db.commit()
                except Exception:
                    own_db.rollback()
                    logger.exception("视频检测失败状态写入失败")
            # 清理 Redis 进度 key，避免脏数据残留
            if "redis_client" in locals() and redis_client:
                try:
                    redis_client.delete(f"video:progress:{owner_task_id}")
                except Exception:
                    pass
            raise
        finally:
            own_db.close()

    def detect_zip(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        zip_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> List[DetectionTask]:
        """
        ZIP 批量检测：解压 ZIP 文件，对其中每张图片执行检测

        处理流程：
        1. 解压 ZIP 到内存
        2. 过滤出支持的图片格式（jpg/jpeg/png/bmp/webp）
        3. 对每张图片调用 detect_single 执行检测
        4. 返回所有检测任务列表

        Args:
            db: 数据库会话
            user_id: 用户 ID
            scene_id: 场景 ID
            zip_bytes: ZIP 文件字节数据
            filename: 原始 ZIP 文件名
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU 阈值
            image_size: 推理图像尺寸

        Returns:
            检测任务列表
        """
        # 0. 校验 scene_id 是否存在（避免外键约束违反导致 500 错误）
        scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            raise ValueError(f"场景不存在 (scene_id={scene_id})")
        import zipfile

        # ZIP 文件大小检查
        if len(zip_bytes) > settings.ZIP_MAX_SIZE_MB * 1024 * 1024:
            from fastapi import HTTPException as FastAPIHTTPException
            raise FastAPIHTTPException(
                status_code=413,
                detail=f"ZIP 文件超过最大限制 ({settings.ZIP_MAX_SIZE_MB} MB)",
            )

        # 支持的图片扩展名
        SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        tasks: List[DetectionTask] = []
        errors: List[dict] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                # 遍历 ZIP 中的所有文件
                file_list = [info for info in zf.infolist() if not info.is_dir()]
                logger.info(
                    "ZIP 检测开始: filename=%s, total_files=%d",
                    filename, len(file_list),
                )

                # 第一遍：收集所有图片文件信息
                image_files: List[tuple] = []  # (info, inner_name, ext)
                for info in file_list:
                    # 提取文件名（处理中文编码）
                    try:
                        inner_name = info.filename.encode("cp437").decode("gbk")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            inner_name = info.filename.encode("cp437").decode("utf-8")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            inner_name = info.filename

                    # 检查扩展名
                    ext = Path(inner_name).suffix.lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        logger.debug("跳过非图片文件: %s", inner_name)
                        continue

                    image_files.append((info, inner_name, ext))

                # 检查图片数量限制
                if len(image_files) > settings.ZIP_MAX_IMAGES:
                    from fastapi import HTTPException as FastAPIHTTPException
                    raise FastAPIHTTPException(
                        status_code=400,
                        detail=f"ZIP 包内图片数量超过限制 ({settings.ZIP_MAX_IMAGES} 张)",
                    )

                # 第二遍：逐张检测
                for info, inner_name, ext in image_files:
                    # 读取图片数据
                    try:
                        image_bytes = zf.read(info)
                        if not image_bytes:
                            continue

                        # 调用单图检测
                        task = self.detect_single(
                            db=db,
                            user_id=user_id,
                            scene_id=scene_id,
                            image_file=image_bytes,
                            filename=Path(inner_name).name or f"image{ext}",
                            conf_threshold=conf_threshold,
                            iou_threshold=iou_threshold,
                            image_size=image_size,
                        )
                        tasks.append(task)
                    except Exception as e:
                        logger.error("ZIP 中图片检测失败: %s, error=%s", inner_name, e)
                        errors.append({"file": inner_name, "error": str(e)})
                        continue

        except zipfile.BadZipFile as e:
            logger.error("ZIP 文件格式错误: %s", e)
            raise ValueError(f"无效的 ZIP 文件: {str(e)}") from e
        except Exception as e:
            logger.exception("ZIP 检测异常: filename=%s", filename)
            raise

        logger.info(
            "ZIP 检测完成: filename=%s, success=%d, errors=%d",
            filename, len(tasks), len(errors),
        )

        return tasks

    def detect_frame(
        self,
        frame_bytes: bytes,
        scene_id: int = 1,
        conf: float = 0.25,
        iou: float = 0.45,
        image_size: int = 640,
        device: str = "cpu",
    ) -> dict:
        """纯推理方法，用于WebSocket摄像头实时检测。无DB/MinIO操作。"""
        import base64

        # 1. 解码JPEG帧
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("无法解码帧图像")

        # 2. 加载模型（_load_model 支持 db=None 时使用缓存）
        model = self._load_model(None, scene_id)

        # 3. 推理
        results = model(frame, conf=conf, iou=iou, imgsz=image_size, device=device, save=False, verbose=False)

        # 4. 绘制标注框
        annotated = results[0].plot()

        # 5. 编码标注帧
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')

        # 6. 提取检测框信息
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": results[0].names[cls_id],
                "confidence": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),
            })

        # 统计 fire 和 smoke 数量、面积
        image_area = frame.shape[1] * frame.shape[0]
        fire_count = 0
        smoke_count = 0
        fire_area_sum = 0.0
        smoke_area_sum = 0.0
        for d in detections:
            cls_name = d.get("class", "")
            x1, y1, x2, y2 = d.get("bbox", [0, 0, 0, 0])
            area = max(0.0, (x2 - x1) * (y2 - y1))
            if cls_name == "fire":
                fire_count += 1
                fire_area_sum += area
            elif cls_name == "smoke":
                smoke_count += 1
                smoke_area_sum += area

        # 火情等级判定：与 fire_level_service 保持一致，烟雾场景也能触发 notice
        from app.services.fire_level_service import fire_level_service

        fire_level_result = fire_level_service.judge(
            fire_count=fire_count,
            smoke_count=smoke_count,
            fire_area=fire_area_sum / image_area if image_area > 0 else 0.0,
            smoke_area=smoke_area_sum / image_area if image_area > 0 else 0.0,
        )

        return {
            "annotated_frame": annotated_b64,
            "detections": detections,
            "total_objects": len(detections),
            "object_count": len(detections),
            "fire_level": fire_level_result["fire_level"],
            "fire_count": fire_count,
            "smoke_count": smoke_count,
        }

    def _load_model(self, db: Optional[Session], scene_id: int):
        """加载场景默认模型（带 LRU 缓存，最大 MAX_CACHE_SIZE 个）
        
        当 db=None 时（如 detect_frame 纯推理场景），仅从缓存加载或使用默认模型。
        
        模型路径解析优先级：
        1. DB 中场景绑定的默认模型（db 不为 None 时）
        2. settings.DEFAULT_MODEL_PATH（相对于后端根目录解析）
        3. 后端根目录下的 yolo11n.pt（本地文件，不触发网络下载）
        4. 最后才尝试 YOLO("yolov11n.pt")（会触发网络下载，仅作兜底）
        """
        with self._lock:
            if scene_id in self._model_cache:
                # 移到末尾表示最近使用
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

        from ultralytics import YOLO

        # 后端根目录绝对路径：detection_service.py → services/ → app/ → backend/
        _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

        model_version = None
        if db is not None:
            # 查找场景默认模型版本
            model_version = (
                db.query(ModelVersion)
                .filter(ModelVersion.scene_id == scene_id, ModelVersion.is_default == True)
                .first()
            )

        with self._lock:
            # 确保模型使用确定性推理，避免 CPU 浮点非确定性导致结果随机波动
            torch.use_deterministic_algorithms(True, warn_only=True)

            # 加锁后再次检查，避免并发重复加载
            if scene_id in self._model_cache:
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

            if model_version and model_version.model_path and os.path.exists(model_version.model_path):
                logger.info("使用场景绑定模型: scene_id=%s, path=%s", scene_id, model_version.model_path)
                model = YOLO(model_version.model_path)
            elif settings.DEFAULT_MODEL_PATH:
                # 将 DEFAULT_MODEL_PATH 解析为绝对路径（相对于后端根目录）
                model_path = Path(settings.DEFAULT_MODEL_PATH)
                # 防御性兜底：如果 DEFAULT_MODEL_PATH 是通用 COCO 模型，自动切换到火灾烟雾专用模型
                if model_path.name in ("yolo11n.pt", "yolov11n.pt"):
                    fire_smoke_path = Path(settings.FIRE_SMOKE_MODEL_PATH)
                    if not fire_smoke_path.is_absolute():
                        fire_smoke_path = _BACKEND_ROOT / fire_smoke_path
                    if fire_smoke_path.exists():
                        logger.info("DEFAULT_MODEL_PATH 是通用模型，自动切换到火灾烟雾模型: %s", fire_smoke_path)
                        model_path = fire_smoke_path
                if not model_path.is_absolute():
                    model_path = _BACKEND_ROOT / model_path
                if model_path.exists():
                    logger.info("使用 DEFAULT_MODEL_PATH: %s", model_path)
                    model = YOLO(str(model_path))
                else:
                    # DEFAULT_MODEL_PATH 指定的文件不存在，尝试本地 yolo11n.pt
                    fallback = _BACKEND_ROOT / "yolo11n.pt"
                    if fallback.exists():
                        logger.warning("DEFAULT_MODEL_PATH 不存在(%s)，使用本地: %s", model_path, fallback)
                        model = YOLO(str(fallback))
                    else:
                        logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                        model = YOLO("yolov11n.pt")
            else:
                # 无 DEFAULT_MODEL_PATH，优先使用本地 yolo11n.pt（绝对路径，不触发下载）
                fallback = _BACKEND_ROOT / "yolo11n.pt"
                if fallback.exists():
                    logger.info("使用本地 yolo11n.pt: %s", fallback)
                    model = YOLO(str(fallback))
                else:
                    logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                    model = YOLO("yolov11n.pt")

            # LRU 淘汰：超出上限时移除最久未使用的模型
            if len(self._model_cache) >= self.MAX_CACHE_SIZE:
                oldest_key = next(iter(self._model_cache))
                del self._model_cache[oldest_key]
                logger.info("模型缓存已满，淘汰最旧模型: scene_id=%s", oldest_key)

            self._model_cache[scene_id] = model

        logger.info("检测模型已加载: scene_id=%s", scene_id)
        return model


# 单例
detection_service = DetectionService()