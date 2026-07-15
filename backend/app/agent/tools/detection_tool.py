"""Attachment-ID based fire and smoke detection tools for the chat agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from langchain_core.tools import BaseTool, ToolException, tool
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.detection_service import detection_service


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".mkv", ".mov", ".mp4"}
ZIP_SUFFIXES = {".zip"}


class SingleImageInput(BaseModel):
    attachment_id: str = Field(min_length=1, description="Authenticated chat attachment ID")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class BatchImagesInput(BaseModel):
    attachment_ids: list[str] = Field(min_length=1, max_length=20, description="Authenticated chat attachment IDs")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class ZipImagesInput(SingleImageInput):
    pass


class VideoInput(SingleImageInput):
    frame_skip: int = Field(default=5, ge=1, le=120)


@dataclass(frozen=True)
class DetectionToolRuntime:
    """Authenticated dependencies that are never exposed in an LLM schema."""

    user_id: int
    db: Any
    attachment_resolver: Callable[[str], Any] | None = None
    service: Any = detection_service
    stub_mode: bool = field(default_factory=lambda: settings.LLM_STUB_MODE)

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.stub_mode and self.attachment_resolver is None:
            raise ValueError("attachment_resolver is required when stub mode is disabled")


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _resolve(runtime: DetectionToolRuntime, attachment_id: str, suffixes: set[str], max_bytes: int) -> Any:
    try:
        attachment = runtime.attachment_resolver(attachment_id) if runtime.attachment_resolver else None
    except Exception as exc:
        raise ToolException("Attachment could not be resolved") from exc
    if attachment is None:
        raise ToolException("Attachment could not be resolved")
    if Path(getattr(attachment, "file_name", "")).suffix.lower() not in suffixes:
        raise ToolException("Attachment type is not valid for this detection tool")
    data = getattr(attachment, "data", b"")
    if not isinstance(data, bytes) or not data:
        raise ToolException("Attachment content is unavailable")
    if len(data) > max_bytes:
        raise ToolException("Attachment exceeds the allowed size")
    return attachment


def _task_payload(task: Any) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "status": task.status,
        "fire_level": task.fire_level,
        "fire_count": task.fire_object_count,
        "smoke_count": task.smoke_object_count,
        "annotated_url": task.annotated_url,
        "error_message": task.error_message,
    }


def build_detection_tools(runtime: DetectionToolRuntime) -> list[BaseTool]:
    """Build tools bound to a single authenticated user and database session."""

    @tool("detect_single_image", args_schema=SingleImageInput)
    def detect_single_image(attachment_id: str, scene_id: int, conf_threshold: float = 0.25, iou_threshold: float = 0.45, image_size: int = 640) -> str:
        """Detect one uploaded image by its attachment ID."""
        if runtime.stub_mode:
            return _json({"status": "simulated", "stub": True, "attachment_ids": [attachment_id]})
        attachment = _resolve(runtime, attachment_id, IMAGE_SUFFIXES, settings.CHAT_ATTACHMENT_MAX_IMAGE_BYTES)
        task = runtime.service.detect_single(db=runtime.db, user_id=runtime.user_id, scene_id=scene_id, image_file=attachment.data, filename=attachment.file_name, conf_threshold=conf_threshold, iou_threshold=iou_threshold, image_size=image_size)
        return _json(_task_payload(task))

    @tool("detect_batch_images", args_schema=BatchImagesInput)
    def detect_batch_images(attachment_ids: list[str], scene_id: int, conf_threshold: float = 0.25, iou_threshold: float = 0.45, image_size: int = 640) -> str:
        """Detect up to 20 uploaded images by their attachment IDs."""
        if runtime.stub_mode:
            return _json({"status": "simulated", "stub": True, "attachment_ids": attachment_ids})
        attachments = [_resolve(runtime, item, IMAGE_SUFFIXES, settings.CHAT_ATTACHMENT_MAX_IMAGE_BYTES) for item in attachment_ids]
        tasks = runtime.service.detect_batch(db=runtime.db, user_id=runtime.user_id, scene_id=scene_id, image_files=[item.data for item in attachments], filenames=[item.file_name for item in attachments], conf_threshold=conf_threshold, iou_threshold=iou_threshold, image_size=image_size)
        return _json({"status": "completed", "total": len(tasks), "tasks": [_task_payload(task) for task in tasks]})

    @tool("detect_zip_images_file", args_schema=ZipImagesInput)
    def detect_zip_images_file(attachment_id: str, scene_id: int, conf_threshold: float = 0.25, iou_threshold: float = 0.45, image_size: int = 640) -> str:
        """Detect images contained in one uploaded ZIP attachment."""
        if runtime.stub_mode:
            return _json({"status": "simulated", "stub": True, "attachment_ids": [attachment_id]})
        attachment = _resolve(runtime, attachment_id, ZIP_SUFFIXES, settings.CHAT_ATTACHMENT_MAX_ZIP_BYTES)
        detect_zip = getattr(runtime.service, "detect_zip", None)
        if detect_zip is None:
            raise ToolException("ZIP detection service is not implemented")
        result = detect_zip(db=runtime.db, user_id=runtime.user_id, scene_id=scene_id, zip_bytes=attachment.data, filename=attachment.file_name, conf_threshold=conf_threshold, iou_threshold=iou_threshold, image_size=image_size)
        return _json(result if not isinstance(result, list) else {"status": "completed", "total": len(result), "tasks": [_task_payload(task) for task in result]})

    @tool("detect_video_file", args_schema=VideoInput)
    def detect_video_file(attachment_id: str, scene_id: int, conf_threshold: float = 0.25, iou_threshold: float = 0.45, image_size: int = 640, frame_skip: int = 5) -> str:
        """Detect one uploaded video by its attachment ID."""
        if runtime.stub_mode:
            return _json({"status": "simulated", "stub": True, "attachment_ids": [attachment_id]})
        attachment = _resolve(runtime, attachment_id, VIDEO_SUFFIXES, settings.CHAT_ATTACHMENT_MAX_VIDEO_BYTES)
        task = runtime.service.detect_video(db=runtime.db, user_id=runtime.user_id, scene_id=scene_id, video_bytes=attachment.data, filename=attachment.file_name, conf_threshold=conf_threshold, iou_threshold=iou_threshold, image_size=image_size, frame_skip=frame_skip)
        return _json(_task_payload(task))

    return [detect_single_image, detect_batch_images, detect_zip_images_file, detect_video_file]


def _unscoped_tool_error() -> str:
    return _json({"status": "rejected", "message": "Use an authenticated attachment_id workflow; unscoped tools cannot access files."})


@tool("detect_single_image")
def detect_single_image(attachment_id: str, scene_id: int) -> str:
    """Compatibility declaration for Agent discovery; runtime binding is required."""
    return _unscoped_tool_error()


@tool("detect_batch_images")
def detect_batch_images(attachment_ids: list[str], scene_id: int) -> str:
    """Compatibility declaration for Agent discovery; runtime binding is required."""
    return _unscoped_tool_error()


@tool("detect_zip_images_file")
def detect_zip_images_file(attachment_id: str, scene_id: int) -> str:
    """Compatibility declaration for Agent discovery; runtime binding is required."""
    return _unscoped_tool_error()


@tool("detect_video_file")
def detect_video_file(attachment_id: str, scene_id: int) -> str:
    """Compatibility declaration for Agent discovery; runtime binding is required."""
    return _unscoped_tool_error()


__all__ = ["DetectionToolRuntime", "build_detection_tools", "detect_single_image", "detect_batch_images", "detect_zip_images_file", "detect_video_file"]
