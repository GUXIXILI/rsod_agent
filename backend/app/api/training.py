"""
训练 API 路由

提供训练任务管理接口：
- POST /api/training/start    — 启动训练
- GET  /api/training/tasks    — 获取任务列表
- GET  /api/training/status/{task_id}   — 获取训练状态（前端轮询）
- GET  /api/training/metrics/{task_id}  — 获取所有 epoch 指标
- POST /api/training/stop/{task_id}     — 停止训练
- GET  /api/training/results/{task_uuid} — 下载 results.csv
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.db_models import DetectionScene, TrainingTask
from app.entity.schemas import (
    TrainingMetricResponse,
    TrainingTaskCreate,
    TrainingTaskResponse,
)
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