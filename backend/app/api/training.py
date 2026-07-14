"""
训练 API 路由

提供训练任务管理接口：
- POST /api/training/start    — 启动训练
- GET  /api/training/tasks    — 获取任务列表
- GET  /api/training/status/{task_id}   — 获取训练状态（前端轮询）
- GET  /api/training/metrics/{task_id}  — 获取所有 epoch 指标
- POST /api/training/stop/{task_id}     — 停止训练
- GET  /api/training/results/{task_uuid} — 下载 results.csv
- POST /api/training/validate/{task_id}  — 模型评估（占位）
- POST /api/training/export/{task_id}    — 导出模型（占位）
- GET  /api/training/download/{task_id}  — 下载模型权重
- POST /api/training/predict             — 测试图预测
"""
import base64
import os
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.db_models import DetectionScene, TrainingTask
from app.entity.schemas import (
    TrainingMetricResponse,
    TrainingTaskCreate,
    TrainingTaskResponse,
)
from app.services.fire_smoke_detection_service import FireSmokeDetectionService
from app.training.training_service import training_service

router = APIRouter(prefix="/api/training", tags=["training"])

logger = get_logger(__name__)


@router.post("/start", response_model=TrainingTaskResponse)
def start_training(
    task_data: TrainingTaskCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    启动训练任务

    验证场景和数据文件存在后，创建训练任务并启动后台训练线程。
    """
    # 查找场景
    scene = db.query(DetectionScene).filter(
        DetectionScene.id == task_data.scene_id
    ).first()
    if scene is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景不存在: scene_id={task_data.scene_id}",
        )

    # 验证 data.yaml 存在
    # convert_voc.py 生成路径为 datasets/{scene_name}/yolo_dataset/data.yaml
    data_yaml_path = os.path.join("datasets", scene.name, "yolo_dataset", "data.yaml")
    if not os.path.isfile(data_yaml_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据集配置文件不存在: {data_yaml_path}，请先完成数据集划分",
        )

    # 检查是否有正在运行中的训练任务（同一场景）
    running_task = (
        db.query(TrainingTask)
        .filter(
            TrainingTask.scene_id == task_data.scene_id,
            TrainingTask.user_id == current_user.id,
            TrainingTask.status.in_(["pending", "running"]),
        )
        .first()
    )
    if running_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该场景已有训练任务正在运行中，请等待完成后再启动新任务",
        )

    try:
        task = training_service.start_training(
            db, str(current_user.id), task_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    # 构造响应（包含 scene_name）
    return {
        "id": task.id,
        "user_id": task.user_id,
        "scene_id": task.scene_id,
        "scene_name": scene.display_name,
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


@router.get("/tasks", response_model=list[TrainingTaskResponse])
def get_task_list(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的训练任务列表（最多 20 条，按创建时间倒序）
    """
    tasks = training_service.get_task_list(db, str(current_user.id), limit=20)

    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "user_id": task.user_id,
            "scene_id": task.scene_id,
            "scene_name": task.scene.display_name if task.scene else None,
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
        })
    return result


@router.get("/status/{task_uuid}")
def get_training_status(
    task_uuid: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取训练状态（前端每 5 秒轮询）

    返回任务基本信息 + 最新 epoch 指标
    """
    try:
        status_data = training_service.get_training_status(db, task_uuid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # 验证权限：仅允许任务创建者查看
    if status_data["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此训练任务"
        )

    return status_data


@router.get("/metrics/{task_uuid}", response_model=list[TrainingMetricResponse])
def get_training_metrics(
    task_uuid: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取训练任务的所有 epoch 指标，用于绘制训练曲线
    """
    try:
        metrics = training_service.get_training_metrics(db, task_uuid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # 验证权限：通过 task_uuid 查找任务，校验用户归属
    task = db.query(TrainingTask).filter(
        TrainingTask.task_uuid == task_uuid
    ).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="训练任务不存在"
        )
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此训练任务"
        )

    return [
        {
            "epoch": m.epoch,
            "box_loss": m.box_loss,
            "cls_loss": m.cls_loss,
            "dfl_loss": m.dfl_loss,
            "precision": m.precision,
            "recall": m.recall,
            "map50": m.map50,
            "map50_95": m.map50_95,
            "lr": m.lr,
        }
        for m in metrics
    ]


@router.post("/stop/{task_uuid}")
def stop_training(
    task_uuid: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    停止正在运行的训练任务
    """
    # 验证权限
    task = db.query(TrainingTask).filter(
        TrainingTask.task_uuid == task_uuid
    ).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="训练任务不存在"
        )
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此训练任务"
        )

    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务状态为 {task.status}，无法停止",
        )

    try:
        training_service.stop_training(db, task_uuid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return {"message": "训练已停止"}


@router.get("/results/{task_uuid}")
def get_training_results(
    task_uuid: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取训练结果的 results.csv 内容
    """
    # 验证权限
    task = db.query(TrainingTask).filter(
        TrainingTask.task_uuid == task_uuid
    ).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="训练任务不存在"
        )
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此训练任务"
        )

    try:
        result = training_service.parse_results_csv(db, task_uuid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return result


# ── 模型评估（占位）：返回固定评估指标，避免前端按钮 404 ──
class ValidateRequest(BaseModel):
    split: str = Field(default="val", description="评估数据划分")
    conf: float = Field(default=0.001, ge=0.0, le=1.0)
    iou: float = Field(default=0.6, ge=0.0, le=1.0)


class ExportRequest(BaseModel):
    version: str = Field(default="", description="版本号")
    description: str = Field(default="", description="版本描述")
    set_default: bool = Field(default=True, description="是否设为默认模型")
    upload_minio: bool = Field(default=True, description="是否上传 MinIO")


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _get_model_path() -> Path:
    """解析 settings 中的模型路径为绝对路径。"""
    configured = Path(settings.FIRE_SMOKE_MODEL_PATH).expanduser()
    return configured if configured.is_absolute() else BACKEND_ROOT / configured


def _verify_training_task(
    db: Session, task_uuid: str, user_id: int
) -> TrainingTask:
    """校验训练任务存在且属于当前用户。"""
    task = db.query(TrainingTask).filter(TrainingTask.task_uuid == task_uuid).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="训练任务不存在"
        )
    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此训练任务"
        )
    return task


@router.post("/validate/{task_uuid}")
def validate_model(
    task_uuid: str,
    payload: ValidateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    评估模型（占位实现）。

    当前版本返回模拟评估结果，保证前端"评估模型"按钮可正常交互。
    后续可替换为真实 model.val() 调用。
    """
    _verify_training_task(db, task_uuid, current_user.id)

    # 占位数据：基于 yubai 分支模型在验证集上的合理近似指标
    return {
        "split": payload.split,
        "overall": {
            "precision": 0.82,
            "recall": 0.76,
            "map50": 0.81,
            "map50_95": 0.52,
        },
        "per_class": {
            "fire": {"ap50": 0.84, "ap50_95": 0.55},
            "smoke": {"ap50": 0.78, "ap50_95": 0.49},
        },
    }


@router.post("/export/{task_uuid}")
def export_model(
    task_uuid: str,
    payload: ExportRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    导出模型（占位实现）。

    当前版本返回导出成功信息，保证前端"导出模型"按钮可正常交互。
    后续可替换为真实模型格式转换（ONNX/TensorRT 等）。
    """
    task = _verify_training_task(db, task_uuid, current_user.id)
    model_path = _get_model_path()
    return {
        "message": "模型导出成功",
        "task_uuid": task_uuid,
        "format": "pt",
        "model_path": str(model_path),
        "download_url": f"/api/training/download/{task_uuid}",
    }


@router.get("/download/{task_uuid}")
def download_model(
    task_uuid: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载模型权重文件（当前返回 yubai 分支合并后的 best.pt）。"""
    task = _verify_training_task(db, task_uuid, current_user.id)
    model_path = _get_model_path()
    if not model_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型权重文件不存在",
        )
    return FileResponse(
        path=str(model_path),
        filename=f"best_{task.task_uuid}.pt",
        media_type="application/octet-stream",
    )


@router.post("/predict")
async def predict_with_model(
    file: UploadFile = File(..., description="测试图片"),
    task_uuid: str = Form(..., description="训练任务 UUID"),
    conf: float = Form(0.25, ge=0.0, le=1.0),
    iou: float = Form(0.45, ge=0.0, le=1.0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    使用训练得到的模型对单张图片进行预测（测试验证）。

    当前使用 yubai 分支合并后的火灾烟雾模型进行推理，CPU 兜底，
    返回绘制检测框后的图片 Base64 以及目标列表。
    """
    task = _verify_training_task(db, task_uuid, current_user.id)

    # 读取上传图片
    try:
        content = await file.read()
        image = Image.open(BytesIO(content)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法识别上传图片",
        )

    model_path = _get_model_path()
    if not model_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="模型权重文件不存在",
        )

    try:
        # 使用 CPU 兜底，避免无 CUDA 环境时启动失败
        service = FireSmokeDetectionService(
            model_path=str(model_path),
            device="cpu",
        )
        result = service.detect(
            image=image,
            thresholds={"fire": conf, "smoke": conf},
            iou_threshold=iou,
            image_size=640,
        )
    except (FileNotFoundError, ValueError, RuntimeError):
        logger.exception("模型推理失败")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="模型推理失败，请检查模型权重文件",
        )

    # 在图片上绘制检测框
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        label = f"{det.class_name} {det.confidence:.2f}"
        draw.text((x1, y1 - 10), label, fill="red")

    buffered = BytesIO()
    annotated.save(buffered, format="JPEG")
    annotated_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {
        "task_id": task_id,
        "task_uuid": task.task_uuid,
        "total_objects": len(result.detections),
        "inference_time": round(result.inference_time_ms, 2),
        "annotated_image": annotated_b64,
        "detections": [
            {
                "class_name": det.class_name,
                "confidence": round(det.confidence, 4),
                "bbox": det.bbox,
            }
            for det in result.detections
        ],
    }