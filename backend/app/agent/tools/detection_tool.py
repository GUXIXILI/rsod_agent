"""Expose persisted fire/smoke detection workflows as LangChain tools."""

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
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_ZIP_BYTES = 200 * 1024 * 1024


class SingleImageInput(BaseModel):
    """Arguments for a single-image detection request."""

    attachment_id: str = Field(min_length=1, description="Opaque ID returned by the chat attachment upload API")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class BatchImagesInput(BaseModel):
    """Arguments for a batch image detection request."""

    attachment_ids: list[str] = Field(min_length=1, max_length=20, description="Opaque IDs returned by the chat attachment upload API")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class ZipImagesInput(BaseModel):
    """Arguments for a ZIP image detection request."""

    attachment_id: str = Field(min_length=1, description="Opaque ID returned by the chat attachment upload API")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)


class VideoInput(BaseModel):
    """Arguments for a video detection request."""

    attachment_id: str = Field(min_length=1, description="Opaque ID returned by the chat attachment upload API")
    scene_id: int = Field(gt=0, description="Detection scene ID")
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    image_size: int = Field(default=640, ge=320, le=1280)
    frame_skip: int = Field(default=5, ge=1, le=120)


@dataclass(frozen=True)
class DetectionToolRuntime:
    """Application-owned dependencies that never appear in an LLM tool schema."""

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


def _json_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _stub_payload(mode: str, scene_id: int, attachment_ids: list[str]) -> str:
    return _json_payload(
        {
            "mode": mode,
            "status": "simulated",
            "stub": True,
            "scene_id": scene_id,
            "attachment_ids": attachment_ids,
            "message": "LLM_STUB_MODE is enabled; model inference was not run.",
        }
    )


def _resolve_attachment(
    runtime: DetectionToolRuntime,
    attachment_id: str,
    suffixes: set[str],
    max_bytes: int,
) -> Any:
    try:
        attachment = runtime.attachment_resolver(attachment_id) if runtime.attachment_resolver else None
    except Exception as exc:
        raise ToolException("Attachment could not be resolved") from exc
    if attachment is None:
        raise ToolException("Attachment could not be resolved")
    file_name = getattr(attachment, "file_name", "")
    data = getattr(attachment, "data", b"")
    suffix = Path(file_name).suffix.lower()
    if suffix not in suffixes:
        raise ToolException("Attachment type is not valid for this detection tool")
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
    """Build four file-detection tools bound to one authenticated user and DB session."""

    @tool("detect_single_image", args_schema=SingleImageInput)
    def detect_single_image(
        attachment_id: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """Detect one uploaded image by its attachment ID."""
        if runtime.stub_mode:
            return _stub_payload("single_image", scene_id, [attachment_id])
        attachment = _resolve_attachment(runtime, attachment_id, IMAGE_SUFFIXES, MAX_IMAGE_BYTES)
        task = runtime.service.detect_single(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            image_file=attachment.data,
            filename=attachment.file_name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return _json_payload(_task_payload(task))

    @tool("detect_batch_images", args_schema=BatchImagesInput)
    def detect_batch_images(
        attachment_ids: list[str],
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """Detect up to 20 uploaded images by their attachment IDs."""
        if runtime.stub_mode:
            return _stub_payload("batch_images", scene_id, attachment_ids)
        attachments = [
            _resolve_attachment(runtime, attachment_id, IMAGE_SUFFIXES, MAX_IMAGE_BYTES)
            for attachment_id in attachment_ids
        ]
        tasks = runtime.service.detect_batch(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            image_files=[attachment.data for attachment in attachments],
            filenames=[attachment.file_name for attachment in attachments],
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return _json_payload({"status": "completed", "total": len(tasks), "tasks": [_task_payload(task) for task in tasks]})

    @tool("detect_zip_images_file", args_schema=ZipImagesInput)
    def detect_zip_images_file(
        attachment_id: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> str:
        """Detect images in one uploaded ZIP file by its attachment ID."""
        if runtime.stub_mode:
            return _stub_payload("zip_images", scene_id, [attachment_id])
        attachment = _resolve_attachment(runtime, attachment_id, {".zip"}, MAX_ZIP_BYTES)
        detect_zip = getattr(runtime.service, "detect_zip", None)
        if detect_zip is None:
            raise ToolException("ZIP detection service is not implemented")
        result = detect_zip(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            zip_bytes=attachment.data,
            filename=attachment.file_name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        if isinstance(result, list):
            result = {"status": "completed", "total": len(result), "tasks": [_task_payload(task) for task in result]}
        return _json_payload(result)

    @tool("detect_video_file", args_schema=VideoInput)
    def detect_video_file(
        attachment_id: str,
        scene_id: int,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        frame_skip: int = 5,
    ) -> str:
        """Detect one uploaded video by its attachment ID."""
        if runtime.stub_mode:
            return _stub_payload("video", scene_id, [attachment_id])
        attachment = _resolve_attachment(runtime, attachment_id, VIDEO_SUFFIXES, MAX_VIDEO_BYTES)
        task = runtime.service.detect_video(
            db=runtime.db,
            user_id=runtime.user_id,
            scene_id=scene_id,
            video_bytes=attachment.data,
            filename=attachment.file_name,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
            frame_skip=frame_skip,
        )
        return _json_payload(_task_payload(task))

    return [detect_single_image, detect_batch_images, detect_zip_images_file, detect_video_file]


__all__ = ["DetectionToolRuntime", "build_detection_tools"]
