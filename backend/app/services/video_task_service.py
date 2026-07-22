"""
视频异步任务管理服务

封装视频异步检测的任务创建、后台线程启动和进度查询逻辑：
- submit_video_task: 创建 DetectionTask + 启动后台处理线程
- get_task_progress: 查询任务进度（Redis → DB → 内存字典三级兜底）
"""
import json
import threading
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask
from app.services.detection_service import detection_service

logger = get_logger(__name__)


class VideoTaskService:
    """视频异步任务管理，使用 Redis + 内存字典 + 线程锁管理进度"""

    _PROGRESS_TTL_SECONDS = 3600  # Redis 进度 key 过期时间（1 小时）

    def __init__(self):
        self._progress: dict = {}       # {task_id: progress_int} 内存兜底
        self._lock = threading.Lock()

    # ── 公开方法 ──────────────────────────────────────

    def submit_video_task(
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
        """创建视频检测任务并启动后台线程处理，立即返回任务记录"""
        # 1. 创建 processing 状态的任务记录
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_type="video",
            file_name=filename,
            status="processing",
            progress=0,
            detected_at=datetime.now(),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        task_id = task.id

        # 2. 初始化 Redis 和内存进度（同步写入 Redis 供检测服务内部读取）
        self._update_progress(task_id, 0)

        # 3. 启动后台线程
        thread = threading.Thread(
            target=self._run_video_detection,
            args=(task_id, user_id, scene_id, video_bytes, filename,
                  conf_threshold, iou_threshold, image_size, frame_skip),
            daemon=True,
        )
        thread.start()

        logger.info("视频异步任务已提交: task_id=%s, filename=%s", task_id, filename)
        return task

    def get_task_progress(self, task_id: int, db: Optional[Session] = None) -> dict:
        """按 Redis → 数据库 → 内存字典的顺序查询任务进度。
        
        优先级设计原因：
        - Redis 性能最高，承载实时进度数据
        - 数据库作为持久化兜底，Redis 缺失或进程重启后可从 DB 恢复
        - 内存字典仅作为最后兜底
        """
        # 第一优先级：Redis（实时进度，性能最高）
        redis_progress = self._read_redis_progress(task_id)
        if redis_progress is not None:
            result = {"task_id": task_id, **redis_progress}
            # 如果传入了 db，补充 DB 中的 status 字段
            if db is not None:
                task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                if task and task.status:
                    result["status"] = task.status
            return result

        # 第二优先级：数据库（Redis 缺失或进程重启后的回退）
        if db is not None:
            task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
            if task:
                return {
                    "task_id": task_id,
                    "progress": int(task.progress or 0),
                    "status": task.status or "unknown",
                }

        # 第三优先级：内存字典（最后兜底）
        with self._lock:
            progress = self._progress.get(task_id)

        if progress is not None:
            return {"task_id": task_id, "progress": progress}

        return {"task_id": task_id, "progress": 0}

    # ── 后台线程逻辑 ──────────────────────────────────

    def _run_video_detection(
        self,
        task_id: int,
        user_id: int,
        scene_id: int,
        video_bytes: bytes,
        filename: str,
        conf_threshold: float,
        iou_threshold: float,
        image_size: int,
        frame_skip: int,
    ):
        """后台线程：执行视频检测并更新进度/状态"""
        thread_db = SessionLocal()
        try:
            # 更新进度：开始处理，同时写入 Redis 和数据库
            self._update_progress(task_id, 10)
            original_task = thread_db.query(DetectionTask).filter(
                DetectionTask.id == task_id
            ).first()
            if original_task:
                original_task.progress = 10
                thread_db.commit()

            # 调用现有 detect_video（传入 progress_task_id 以关联进度）
            task = detection_service.detect_video(
                db=thread_db,
                user_id=user_id,
                scene_id=scene_id,
                video_bytes=video_bytes,
                filename=filename,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                image_size=image_size,
                frame_skip=frame_skip,
                progress_task_id=task_id,
            )

            # 检测完成 → 更新原始 processing 任务的状态
            original_task = thread_db.query(DetectionTask).filter(
                DetectionTask.id == task_id
            ).first()
            if original_task:
                original_task.status = "completed"
                original_task.progress = 100
                original_task.completed_at = datetime.now()
                # 将检测结果关联到原始任务
                original_task.annotated_url = task.annotated_url
                original_task.original_url = task.original_url
                original_task.fire_level = task.fire_level
                original_task.risk_level = task.risk_level
                original_task.fire_area = task.fire_area
                original_task.smoke_area = task.smoke_area
                original_task.fire_object_count = task.fire_object_count
                original_task.smoke_object_count = task.smoke_object_count
                original_task.image_width = task.image_width
                original_task.image_height = task.image_height
                original_task.video_duration = task.video_duration
                thread_db.commit()

            self._update_progress(task_id, 100)
            logger.info("视频异步任务完成: task_id=%s", task_id)

        except Exception as e:
            logger.exception("视频异步任务失败: task_id=%s, error=%s", task_id, e)
            # 更新失败状态
            try:
                original_task = thread_db.query(DetectionTask).filter(
                    DetectionTask.id == task_id
                ).first()
                if original_task:
                    original_task.status = "failed"
                    original_task.error_message = str(e)
                    thread_db.commit()
                # 清理 Redis 进度 key，避免脏数据残留
                self._delete_redis_progress(task_id)
            except Exception:
                logger.exception("更新任务失败状态也出错: task_id=%s", task_id)
                thread_db.rollback()
        finally:
            thread_db.close()

    def _update_progress(self, task_id: int, progress: int):
        """更新内存兜底和 Redis 进度，同步写入两级存储。
        
        Redis 写入失败时不影响内存更新，保证本地进度可用。
        """
        progress = max(0, min(100, int(progress)))
        with self._lock:
            self._progress[task_id] = progress
        # 同步写入 Redis（非致命：写入失败不影响功能）
        client = self._get_redis_client()
        if client is None:
            return
        try:
            client.set(
                f"video:progress:{task_id}",
                json.dumps({"progress": progress}),
                ex=self._PROGRESS_TTL_SECONDS,
            )
        except Exception:
            logger.warning("写入视频任务 Redis 进度失败: task_id=%s", task_id)

    # ── Redis 辅助方法 ──────────────────────────────────

    def _get_redis_client(self):
        """获取 Redis 客户端，连接失败时返回 None（非致命）"""
        try:
            import redis
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            return client
        except Exception:
            return None

    def _read_redis_progress(self, task_id: int) -> dict | None:
        """从 Redis 读取进度数据，失败或无数据返回 None"""
        client = self._get_redis_client()
        if client is None:
            return None
        try:
            raw = client.get(f"video:progress:{task_id}")
            data = json.loads(raw) if raw else None
            if isinstance(data, dict) and "progress" in data:
                data["progress"] = int(data["progress"])
                return data
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("视频任务 Redis 进度格式无效: task_id=%s", task_id)
        except Exception:
            pass
        return None

    def _delete_redis_progress(self, task_id: int) -> None:
        """删除 Redis 中的进度 key（任务完成或失败时清理）"""
        client = self._get_redis_client()
        if client is None:
            return
        try:
            client.delete(f"video:progress:{task_id}")
        except Exception:
            logger.warning("删除视频任务 Redis 进度失败: task_id=%s", task_id)


# 单例
video_task_service = VideoTaskService()
