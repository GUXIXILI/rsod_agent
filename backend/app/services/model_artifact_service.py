"""模型导出与下载制品解析服务。"""

from pathlib import Path

from ultralytics import YOLO

from app.config.settings import settings
from app.entity.db_models import ModelVersion
from app.services.fire_smoke_validation import (
    validate_device,
    validate_image_size,
)


EXPORT_SUFFIXES = {
    "onnx": ".onnx",
    "torchscript": ".torchscript",
}
DOWNLOAD_SUFFIXES = {
    "pt": ".pt",
    **EXPORT_SUFFIXES,
}
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class ModelArtifactError(ValueError):
    """模型制品不存在、格式无效或导出失败。"""


def _get_model_version(db, model_version_id: int) -> ModelVersion:
    model_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == model_version_id)
        .first()
    )
    if model_version is None:
        raise ModelArtifactError(
            f"Model version not found: {model_version_id}"
        )
    return model_version


def _stored_model_path(model_version: ModelVersion) -> Path:
    model_path = Path(model_version.model_path).expanduser().resolve()
    configured_roots = [
        value.strip()
        for value in settings.MODEL_ARTIFACT_ROOTS.split(",")
        if value.strip()
    ]
    allowed_roots = []
    for value in configured_roots:
        root = Path(value).expanduser()
        allowed_roots.append(
            (root if root.is_absolute() else BACKEND_ROOT / root).resolve()
        )
    if not allowed_roots or not any(
        model_path.is_relative_to(root) for root in allowed_roots
    ):
        raise ModelArtifactError(
            "Stored model path is outside allowed model directories"
        )
    if not model_path.is_file():
        raise ModelArtifactError(
            f"Stored model file does not exist: {model_path}"
        )
    return model_path


def export_model_version(
    db,
    model_version_id: int,
    export_format: str,
    imgsz: int = 640,
    device: str = "cpu",
) -> Path:
    """将数据库中的PyTorch模型导出为受支持的通用格式。"""
    if export_format not in EXPORT_SUFFIXES:
        raise ModelArtifactError(
            f"Unsupported export format: {export_format}"
        )
    try:
        validate_image_size(imgsz)
        validate_device(device)
    except ValueError as exc:
        raise ModelArtifactError(str(exc)) from exc

    model_version = _get_model_version(db, model_version_id)
    model_path = _stored_model_path(model_version)
    expected_path = model_path.with_suffix(EXPORT_SUFFIXES[export_format])

    if (
        expected_path.is_file()
        and expected_path.stat().st_mtime >= model_path.stat().st_mtime
    ):
        return expected_path

    try:
        exported = YOLO(str(model_path)).export(
            format=export_format,
            imgsz=imgsz,
            batch=1,
            device=device,
            half=False,
            simplify=False,
            opset=18,
        )
    except Exception as exc:
        raise ModelArtifactError(
            f"Model export failed: {exc}"
        ) from exc

    exported_path = Path(exported).expanduser().resolve()
    if exported_path != expected_path or not exported_path.is_file():
        raise ModelArtifactError(
            f"Exported model file was not generated as expected: {expected_path}"
        )
    return exported_path


def get_model_artifact(
    db,
    model_version_id: int,
    artifact_format: str,
) -> Path:
    """解析允许下载的模型文件，禁止客户端传入任意路径。"""
    if artifact_format not in DOWNLOAD_SUFFIXES:
        raise ModelArtifactError(
            f"Unsupported download format: {artifact_format}"
        )

    model_version = _get_model_version(db, model_version_id)
    model_path = _stored_model_path(model_version)
    artifact_path = (
        model_path
        if artifact_format == "pt"
        else model_path.with_suffix(DOWNLOAD_SUFFIXES[artifact_format])
    )
    if not artifact_path.is_file():
        raise ModelArtifactError(
            f"Model artifact does not exist: {artifact_path}"
        )
    return artifact_path
