"""将现有检测业务服务封装为 LangChain Tool。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, ToolException, tool
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.detection_service import detection_service


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".mkv", ".mov", ".mp4"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_ZIP_BYTES = 200 * 1024 * 1024


class SingleImageInput(BaseModel):
    """单图检测工具参数。"""

    file_path: str = Field(min_length=1, description="服务端已上传图片的绝对路径")
    scene_id: int = Field(gt=0, description="检测场景 ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class BatchImagesInput(BaseModel):
    """批量图片检测工具参数。"""

    file_paths: list[str] = Field(
        min_length=1,
        max_length=20,
        description="服务端已上传图片的绝对路径列表",
    )
    scene_id: int = Field(gt=0, description="检测场景 ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class ZipImagesInput(BaseModel):
    """ZIP 图片集检测工具参数。"""

    file_path: str = Field(min_length=1, description="服务端已上传 ZIP 的绝对路径")
    scene_id: int = Field(gt=0, description="检测场景 ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class VideoInput(BaseModel):
    """视频检测工具参数。"""

    file_path: str = Field(min_length=1, description="服务端已上传视频的绝对路径")
    scene_id: int = Field(gt=0, description="检测场景 ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)
    frame_skip: int = Field(default=5, ge=1, le=120)


@dataclass(frozen=True)
class DetectionToolRuntime:
    """由应用注入的检测上下文，不向大模型暴露用户和数据库对象。"""

    user_id: int
    db: Any
    allowed_file_roots: tuple[Path, ...]
    service: Any = detection_service
    stub_mode: bool = field(default_factory=lambda: settings.LLM_STUB_MODE)

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.allowed_file_roots:
            raise ValueError("At least one allowed file root is required")


def _json_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _stub_payload(mode: str, scene_id: int, files: list[str]) -> str:
    return _json_payload(
        {
            "mode": mode,
            "status": "simulated",
            "stub": True,
            "scene_id": scene_id,
            "files": [Path(item).name for item in files],
            "message": "LLM_STUB_MODE 已启用，未执行真实模型推理。",
        }
    )


def _resolve_file(
    runtime: DetectionToolRuntime,
    file_path: str,
    suffixes: set[str],
    max_bytes: int,
) -> Path:
    candidate = Path(file_path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in runtime.allowed_file_roots]
    if not any(candidate == root or root in candidate.parents for root in roots):
        raise ToolException("文件不在允许的上传目录中")
    if not candidate.is_file():
        raise ToolException("检测文件不存在")
    if candidate.suffix.lower() not in suffixes:
        raise ToolException(f"不支持的文件类型: {candidate.suffix or '无扩展名'}")
    if candidate.stat().st_size > max_bytes:
        raise ToolException("检测文件超过大小限制")
    return candidate


def _task_payload(task: Any) -> dict[str, Any]:
    return {
        "task_id": getattr(task, "id", None),
        "status": getattr(task, "status", None),
        "fire_level": getattr(task, "fire_level", None),
        "fire_count": getattr(task, "fire_object_count", 0) or 0,
        "smoke_count": getattr(task, "smoke_object_count", 0) or 0,
        "annotated_url": getattr(task, "annotated_url", None),
        "error_message": getattr(task, "error_message", None),
    }


def build_detection_tools(runtime: DetectionToolRuntime) -> list[BaseTool]:
    """创建绑定当前用户、数据库和允许目录的四个检测工具。"""

    @tool("detect_single_image", args_schema=SingleImageInput)
    def detect_single_image(
        file_path: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """检测一张已上传图片，返回任务状态、火情等级、目标数量和标注图地址。"""
        if runtime.stub_mode:
            return _stub_payload("single_image", scene_id, [file_path])
        path = _resolve_file(runtime, file_path, IMAGE_SUFFIXES, MAX_IMAGE_BYTES)
        task = runtime.service.detect_single(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            image_file=path.read_bytes(),
            filename=path.name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return _json_payload(_task_payload(task))

    @tool("detect_batch_images", args_schema=BatchImagesInput)
    def detect_batch_images(
        file_paths: list[str],
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """检测最多 20 张已上传图片，返回每张图片对应的检测任务摘要。"""
        if runtime.stub_mode:
            return _stub_payload("batch_images", scene_id, file_paths)
        paths = [
            _resolve_file(runtime, item, IMAGE_SUFFIXES, MAX_IMAGE_BYTES)
            for item in file_paths
        ]
        tasks = runtime.service.detect_batch(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            image_files=[path.read_bytes() for path in paths],
            filenames=[path.name for path in paths],
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return _json_payload(
            {"status": "completed", "total": len(tasks), "tasks": [_task_payload(task) for task in tasks]}
        )

    @tool("detect_zip_images_file", args_schema=ZipImagesInput)
    def detect_zip_images_file(
        file_path: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """检测已上传 ZIP 内的图片；后端 detect_zip 未完成时返回明确错误。"""
        if runtime.stub_mode:
            return _stub_payload("zip_images", scene_id, [file_path])
        path = _resolve_file(runtime, file_path, {".zip"}, MAX_ZIP_BYTES)
        detect_zip = getattr(runtime.service, "detect_zip", None)
        if detect_zip is None:
            raise ToolException("ZIP 检测服务尚未实现")
        result = detect_zip(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            zip_bytes=path.read_bytes(),
            filename=path.name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        if isinstance(result, list):
            result = {"status": "completed", "total": len(result), "tasks": [_task_payload(task) for task in result]}
        return _json_payload(result)

    @tool("detect_video_file", args_schema=VideoInput)
    def detect_video_file(
        file_path: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        frame_skip: int = 5,
    ) -> str:
        """检测一个已上传视频，返回视频检测任务和火情摘要。"""
        if runtime.stub_mode:
            return _stub_payload("video", scene_id, [file_path])
        path = _resolve_file(runtime, file_path, VIDEO_SUFFIXES, MAX_VIDEO_BYTES)
        task = runtime.service.detect_video(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            video_bytes=path.read_bytes(),
            filename=path.name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
            frame_skip=frame_skip,
        )
        return _json_payload(_task_payload(task))

    return [
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
    ]


__all__ = ["DetectionToolRuntime", "build_detection_tools"]
