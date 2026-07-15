"""
MinIO 文件代理 API 路由
- GET /api/files/{bucket}/{filename}  流式代理返回 MinIO 文件
"""
import mimetypes
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from app.api.auth import get_current_user
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# 允许访问的 MinIO 存储桶白名单
ALLOWED_BUCKETS = {"models", "uploads", "results", "avatars", "fire-detection-images"}


@router.get("/{bucket}/{filename:path}")
async def proxy_file(bucket: str, filename: str, current_user=Depends(get_current_user)):
    """
    从 MinIO 流式代理返回文件
    - bucket: 存储桶名称（需在白名单内）
    - filename: 文件路径（支持子目录，如 detection/user1/20250715/img.jpg）
    """
    # 1. 校验 bucket 在白名单内
    if bucket not in ALLOWED_BUCKETS:
        return JSONResponse(
            status_code=403,
            content={"code": 403, "message": "不允许访问此bucket", "data": None},
        )

    # 2. 防止目录遍历攻击
    if ".." in filename or filename.startswith("/"):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "无效的文件名", "data": None},
        )

    # 3. 从 MinIO 获取文件流
    try:
        from app.storage.minio_client import MinIOClient
        minio_client = MinIOClient()
        response = minio_client.get_file_stream(bucket, filename)

        # 4. 推断 Content-Type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"

        logger.info(f"代理文件: bucket={bucket}, filename={filename}, type={content_type}")

        # 5. 返回流式响应（8KB 分块）
        return StreamingResponse(
            response.stream(amt=8192),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as e:
        logger.warning(f"文件未找到: bucket={bucket}, filename={filename}, error={e}")
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "文件未找到", "data": None},
        )
