"""Authenticated fire/smoke image and video-frame inference endpoints."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.config.settings import settings
from app.services.fire_smoke_detection_service import (
    ConfirmationState,
    fire_smoke_detection_service,
    video_confirmation_registry,
)


MAX_IMAGE_BYTES = 20 * 1024 * 1024
router = APIRouter(prefix="/api/detection", tags=["detection"])


class DetectionItemResponse(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    mode: str
    image_width: int
    image_height: int
    inference_time_ms: float
    thresholds: dict[str, float]
    counts: dict[str, int]
    detections: list[DetectionItemResponse]
    confirmation: dict[str, dict[str, Any]] | None = None
    confirmed_classes: list[str] = Field(default_factory=list)
    new_alert_classes: list[str] = Field(default_factory=list)


async def _read_image(file: UploadFile) -> Image.Image:
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image uploads are supported",
        )
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds 20 MiB",
        )
    try:
        return Image.open(BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image",
        ) from exc


def _run_detection(
    image: Image.Image,
    fire_threshold: float,
    smoke_threshold: float,
    iou_threshold: float,
    image_size: int,
):
    try:
        return fire_smoke_detection_service.detect(
            image=image,
            thresholds={
                "fire": fire_threshold,
                "smoke": smoke_threshold,
            },
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _build_response(
    result,
    mode: str,
    thresholds: dict[str, float],
    confirmation: dict[str, ConfirmationState] | None = None,
) -> dict[str, Any]:
    payload = result.to_dict()
    counts = {"fire": 0, "smoke": 0}
    for item in result.detections:
        counts[item.class_name] += 1
    serialized_confirmation = None
    confirmed_classes: list[str] = []
    new_alert_classes: list[str] = []
    if confirmation is not None:
        serialized_confirmation = {
            name: {
                "consecutive_frames": state.consecutive_frames,
                "required_frames": state.required_frames,
                "confirmed": state.confirmed,
                "newly_confirmed": state.newly_confirmed,
            }
            for name, state in confirmation.items()
        }
        confirmed_classes = [
            name for name, state in confirmation.items() if state.confirmed
        ]
        new_alert_classes = [
            name
            for name, state in confirmation.items()
            if state.newly_confirmed
        ]
    return {
        "mode": mode,
        **payload,
        "thresholds": thresholds,
        "counts": counts,
        "confirmation": serialized_confirmation,
        "confirmed_classes": confirmed_classes,
        "new_alert_classes": new_alert_classes,
    }


@router.post("/image", response_model=DetectionResponse)
async def detect_image(
    file: Annotated[UploadFile, File(...)],
    fire_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_IMAGE_FIRE_THRESHOLD,
    smoke_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD,
    iou_threshold: Annotated[float, Form(ge=0.0, le=1.0)] = 0.45,
    image_size: Annotated[int, Form(ge=320, le=1280)] = 640,
    current_user=Depends(get_current_user),
):
    image = await _read_image(file)
    result = _run_detection(
        image,
        fire_threshold,
        smoke_threshold,
        iou_threshold,
        image_size,
    )
    return _build_response(
        result,
        mode="image",
        thresholds={"fire": fire_threshold, "smoke": smoke_threshold},
    )


@router.post("/video/frame", response_model=DetectionResponse)
async def detect_video_frame(
    file: Annotated[UploadFile, File(...)],
    stream_id: Annotated[str, Form(min_length=1, max_length=100)],
    fire_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_VIDEO_FIRE_THRESHOLD,
    smoke_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_VIDEO_SMOKE_THRESHOLD,
    fire_confirm_frames: Annotated[
        int,
        Form(ge=1, le=30),
    ] = settings.FIRE_SMOKE_FIRE_CONFIRM_FRAMES,
    smoke_confirm_frames: Annotated[
        int,
        Form(ge=1, le=30),
    ] = settings.FIRE_SMOKE_SMOKE_CONFIRM_FRAMES,
    iou_threshold: Annotated[float, Form(ge=0.0, le=1.0)] = 0.45,
    image_size: Annotated[int, Form(ge=320, le=1280)] = 640,
    current_user=Depends(get_current_user),
):
    image = await _read_image(file)
    result = _run_detection(
        image,
        fire_threshold,
        smoke_threshold,
        iou_threshold,
        image_size,
    )
    registry_key = f"{current_user.id}:{stream_id}"
    confirmation = video_confirmation_registry.update(
        stream_id=registry_key,
        detections=result.detections,
        required_frames={
            "fire": fire_confirm_frames,
            "smoke": smoke_confirm_frames,
        },
    )
    return _build_response(
        result,
        mode="video_frame",
        thresholds={"fire": fire_threshold, "smoke": smoke_threshold},
        confirmation=confirmation,
    )


@router.delete("/video/{stream_id}")
def reset_video_stream(
    stream_id: str,
    current_user=Depends(get_current_user),
):
    registry_key = f"{current_user.id}:{stream_id}"
    return {
        "stream_id": stream_id,
        "reset": video_confirmation_registry.reset(registry_key),
    }
