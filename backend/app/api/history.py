"""
历史记录 API 路由

提供检测历史记录查询接口：
- GET /api/history/tasks — 分页查询检测历史
- GET /api/history/tasks/{task_id} — 检测任务详情
- DELETE /api/history/tasks/{task_id} — 删除检测记录
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.history_service import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/tasks")
def get_history_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    fire_level: Optional[str] = Query(None, description="火情等级筛选"),
    file_name: Optional[str] = Query(None, description="文件名搜索"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询检测历史记录"""
    result = history_service.get_tasks(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        fire_level=fire_level,
        file_name=file_name,
        start_time=start_time,
        end_time=end_time,
    )
    return {"code": 200, "message": "success", "data": result}


@router.get("/tasks/{task_id}")
def get_history_task_detail(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取检测任务详情"""
    detail = history_service.get_task_detail(db, task_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测任务不存在或无权查看")
    return {"code": 200, "message": "success", "data": detail}


@router.delete("/tasks/{task_id}")
def delete_history_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除检测记录"""
    success = history_service.delete_task(db, task_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测任务不存在或无权删除")
    return {"code": 200, "message": "删除成功"}