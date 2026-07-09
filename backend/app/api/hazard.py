"""
危险路况 API 路由

提供危险路况预测与预警查询接口：
- POST /api/hazard/predict           — 触发路况预测
- GET  /api/hazard/predictions       — 获取预测历史
- GET  /api/hazard/alerts            — 获取预警列表
- POST /api/hazard/alerts/{alert_id}/handle — 标记预警已处理
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.hazard_predict_service import hazard_predict_service
from app.services.alert_service import alert_service

router = APIRouter(prefix="/api/hazard", tags=["hazard"])


class PredictRequest(BaseModel):
    """路况预测请求"""
    location_id: int = Field(..., description="监测点ID")
    horizon_minutes: int = Field(30, ge=5, le=120, description="预测时间窗口（分钟）")


@router.post("/predict")
def predict_hazard(
    request: PredictRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    触发危险路况预测

    结合天气、交通数据，输出风险等级和概率。
    预测结果自动写入数据库，高风险时自动生成预警。
    """
    # 执行预测
    prediction = hazard_predict_service.predict(
        db, request.location_id, request.horizon_minutes
    )

    # 高风险时自动生成预警
    alert = alert_service.create_alert(db, prediction)

    return {
        "prediction": {
            "id": prediction.id,
            "location_id": prediction.location_id,
            "prediction_time": prediction.prediction_time,
            "horizon_minutes": prediction.horizon_minutes,
            "risk_level": prediction.risk_level,
            "risk_probability": prediction.risk_probability,
            "model_type": prediction.model_type,
            "feature_summary": prediction.feature_summary,
        },
        "alert": {
            "id": alert.id,
            "alert_level": alert.alert_level,
            "push_status": alert.push_status,
        } if alert else None,
    }


@router.get("/predictions")
def get_predictions(
    location_id: int = Query(..., description="监测点ID"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定监测点的预测历史"""
    predictions = hazard_predict_service.get_predictions(db, location_id, limit)
    return [
        {
            "id": p.id,
            "location_id": p.location_id,
            "prediction_time": p.prediction_time,
            "horizon_minutes": p.horizon_minutes,
            "risk_level": p.risk_level,
            "risk_probability": p.risk_probability,
            "model_type": p.model_type,
            "feature_summary": p.feature_summary,
        }
        for p in predictions
    ]


@router.get("/alerts")
def get_alerts(
    location_id: int = Query(None, description="监测点ID（可选，不传则返回全部）"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取预警列表"""
    alerts = alert_service.get_alerts(db, location_id, limit)
    return [
        {
            "id": a.id,
            "location_id": a.location_id,
            "alert_level": a.alert_level,
            "content": a.content,
            "channels": a.channels,
            "push_status": a.push_status,
            "handled_status": a.handled_status,
            "created_at": a.created_at,
            "handled_at": a.handled_at,
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/handle")
def handle_alert(
    alert_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记预警为已处理"""
    try:
        alert = alert_service.handle_alert(db, alert_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    return {
        "id": alert.id,
        "handled_status": alert.handled_status,
        "handled_at": alert.handled_at,
    }