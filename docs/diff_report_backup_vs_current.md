# 备份版本与当前版本差异报告

- **备份版本路径**：`d:\clone\rsod_agent_backup_20260717\rsod_agent`
- **当前版本路径**：`d:\clone\rsod_agent`
- **发现差异文件总数**（全量扫描）：35
- **P0 数量**：5
- **P1 数量**：3
- **P2 数量**：0
- **重点文件中无差异**：5
- **重点文件中均不存在**：3

---

### 文件：backend/.env
**优先级**：P0
**影响说明**：当前版本新增 .env 文件，包含 LLM API 密钥、LLM_STUB_MODE 等关键运行时配置；若配置错误会导致真实大模型调用失败或项目无法启动。
**备份版本（原功能）**：该文件在备份版本中不存在。
**当前版本（缺失/被改）**：
```bash
# ═══════════════════════════════════════════════════════
# 火灾与烟雾智能检测平台 — 环境变量配置（本地开发）
# ═══════════════════════════════════════════════════════

# ── 大模型配置 ──────────────────────────────────
# 关闭占位模式，使用真实 LLM API
LLM_STUB_MODE=true

# 对话/Agent 大模型 API（hcnsec.cn 中转平台）
# 平台地址：https://api.hcnsec.cn
QWEN_BASE_URL=https://api.ltzy.top/v1
QWEN_MODEL=deepseek-ai/deepseek-v4-pro
QWEN_API_KEY=acu_QKuC6OcZ0eJ6ddwRb2TPDcEf6p536fIp

# 不使用本地 Ollama
USE_LOCAL_LLM=false

# RAG / Embedding 配置（沿用旧 API，独立密钥）
# 旧平台地址：https://api.ltzy.top
# 旧 API Key：acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
EMBEDDING_BASE_URL=https://api.ltzy.top/v1
EMBEDDING_API_KEY=acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
EMBEDDING_MODEL=baai/bge-m3
OPENAI_API_KEY=

# ── 数据库配置 ───────────────────────────────────────
DB_HOST=localhost
DB_PORT=5433
DB_NAME=rsod_agent
DB_USER=rsod_admin
DB_PASSWORD=rsod_admin

# ── Redis 配置 ───────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379

# ── MinIO 对象存储配置 ───────────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=fire-detection-images
MINIO_SECURE=false

# ── JWT 认证配置 ─────────────────────────────────────
JWT_SECRET_KEY=dev-secret-key-change-in-production-32chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ── 应用配置 ─────────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO

# ── 模型路径配置 ───────────────────────────────────
DEFAULT_MODEL_PATH=models/fire_smoke_yolo11n_v1/best.pt

# ── 火灾烟雾检测配置 ─────────────────────────────────
FIRE_SMOKE_MODEL_PATH=models/fire_smoke_yolo11n_v1/best.pt
FIRE_SMOKE_DEVICE=cpu
FIRE_SMOKE_IMAGE_FIRE_THRESHOLD=0.25
FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD=0.20

# ── CORS 配置 ────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080

# ── 定时任务配置 ─────────────────────────────────────
SCHEDULER_ENABLED=false
```
**统一差异（unified diff）**：
```diff
--- backup/backend/.env
+++ current/backend/.env
@@ -0,0 +1,66 @@
+# ═══════════════════════════════════════════════════════
+# 火灾与烟雾智能检测平台 — 环境变量配置（本地开发）
+# ═══════════════════════════════════════════════════════
+
+# ── 大模型配置 ──────────────────────────────────
+# 关闭占位模式，使用真实 LLM API
+LLM_STUB_MODE=true
+
+# 对话/Agent 大模型 API（hcnsec.cn 中转平台）
+# 平台地址：https://api.hcnsec.cn
+QWEN_BASE_URL=https://api.ltzy.top/v1
+QWEN_MODEL=deepseek-ai/deepseek-v4-pro
+QWEN_API_KEY=acu_QKuC6OcZ0eJ6ddwRb2TPDcEf6p536fIp
+
+# 不使用本地 Ollama
+USE_LOCAL_LLM=false
+
+# RAG / Embedding 配置（沿用旧 API，独立密钥）
+# 旧平台地址：https://api.ltzy.top
+# 旧 API Key：acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
+EMBEDDING_BASE_URL=https://api.ltzy.top/v1
+EMBEDDING_API_KEY=acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
+EMBEDDING_MODEL=baai/bge-m3
+OPENAI_API_KEY=
+
+# ── 数据库配置 ───────────────────────────────────────
+DB_HOST=localhost
+DB_PORT=5433
+DB_NAME=rsod_agent
+DB_USER=rsod_admin
+DB_PASSWORD=rsod_admin
+
+# ── Redis 配置 ───────────────────────────────────────
+REDIS_HOST=localhost
+REDIS_PORT=6379
+
+# ── MinIO 对象存储配置 ───────────────────────────────
+MINIO_ENDPOINT=localhost:9000
+MINIO_ACCESS_KEY=minioadmin
+MINIO_SECRET_KEY=minioadmin
+MINIO_BUCKET=fire-detection-images
+MINIO_SECURE=false
+
+# ── JWT 认证配置 ─────────────────────────────────────
+JWT_SECRET_KEY=dev-secret-key-change-in-production-32chars
+JWT_ALGORITHM=HS256
+ACCESS_TOKEN_EXPIRE_MINUTES=30
+
+# ── 应用配置 ─────────────────────────────────────────
+DEBUG=false
+LOG_LEVEL=INFO
+
+# ── 模型路径配置 ───────────────────────────────────
+DEFAULT_MODEL_PATH=models/fire_smoke_yolo11n_v1/best.pt
+
+# ── 火灾烟雾检测配置 ─────────────────────────────────
+FIRE_SMOKE_MODEL_PATH=models/fire_smoke_yolo11n_v1/best.pt
+FIRE_SMOKE_DEVICE=cpu
+FIRE_SMOKE_IMAGE_FIRE_THRESHOLD=0.25
+FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD=0.20
+
+# ── CORS 配置 ────────────────────────────────────────
+ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
+
+# ── 定时任务配置 ─────────────────────────────────────
+SCHEDULER_ENABLED=false
```
**结论**：确认当前 .env 中的 API 密钥与开关为最终期望配置；如真实 LLM 不可用，应保持 LLM_STUB_MODE=true 作为占位，待资金到位后再改为 false。


---

### 文件：backend/app/agent/tools/detection_tool.py
**优先级**：P0
**影响说明**：检测工具返回格式变化，影响前端能否解析检测框、标注图、火情等级等关键信息。
**备份版本（原功能）**：
```python
"""
检测工具封装模块

将 DetectionService 的 4 个核心检测方法封装为 LangChain @tool 装饰器工具，
供 ReAct Agent 在推理过程中调用。

检测类别：fire（火焰）、smoke（烟雾）
"""

import base64
import json
import os
from typing import List, Optional

from langchain_core.tools import tool

from app.database.session import SessionLocal
from app.entity.db_models import DetectionResult
from app.services.detection_service import detection_service
from app.core.logger import get_logger

logger = get_logger(__name__)


@tool
def detect_single_image(
    image_path: str,
    conf: float = 0.25,
    iou: float = 0.45,
) -> str:
    """对单张图片进行火焰和烟雾目标检测。

    适用场景：用户上传单张图片，需要检测其中是否存在火焰或烟雾。

    Args:
        image_path: 图片文件的本地路径或 MinIO URL。
        conf: 置信度阈值（0.0~1.0），默认 0.25。低于此值的检测结果会被过滤。
        iou: NMS（非极大值抑制）IoU 阈值（0.0~1.0），默认 0.45。用于去除重叠框。

    Returns:
        str: JSON 格式的检测结果，包含文字摘要、标注图 URL/base64、检测框列表等。
    """
    if not image_path:
        return json.dumps({"error": "图片路径为空，请提供有效的图片路径或 URL。"}, ensure_ascii=False)

    try:
        # ── URL 检测分支：如果 image_path 是 HTTP/HTTPS URL，先下载到内存 ──
        if image_path.startswith(("http://", "https://")):
            logger.info("检测到 URL 图片，开始下载: %s", image_path)
            from urllib.parse import urlparse

            # 判断是否为 MinIO 预签名 URL，若是则直接用 MinIO 客户端下载（避免 403）
            from app.storage.minio_client import MinIOClient
            parsed = urlparse(image_path)
            # 从 URL 路径中提取对象名称：/bucket-name/object/path → object/path
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) > 1:
                object_name = path_parts[1].split("?")[0]  # 去掉查询参数
                try:
                    minio = MinIOClient()
                    stream = minio.get_file_stream(minio.bucket_name, object_name)
                    image_bytes = stream.read()
                    stream.close()
                    filename = os.path.basename(object_name) or "downloaded_image.jpg"
                    logger.info("通过 MinIO 客户端下载成功: %s, 大小: %d bytes", object_name, len(image_bytes))
                except Exception as minio_err:
                    # MinIO 客户端下载失败，回退到 HTTP 下载
                    logger.warning("MinIO 客户端下载失败，回退到 HTTP: %s", minio_err)
                    import requests
                    try:
                        response = requests.get(image_path, timeout=30)
                        response.raise_for_status()
                        image_bytes = response.content
                        filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
                        logger.info("HTTP 下载成功，大小: %d bytes", len(image_bytes))
                    except requests.RequestException as e:
                        return json.dumps({"error": f"无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"}, ensure_ascii=False)
            else:
                # 非 MinIO URL，用 HTTP 下载
                import requests
                try:
                    response = requests.get(image_path, timeout=30)
                    response.raise_for_status()
                    image_bytes = response.content
                    filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
                    logger.info("HTTP 下载成功，大小: %d bytes", len(image_bytes))
                except requests.RequestException as e:
                    return json.dumps({"error": f"无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"}, ensure_ascii=False)
        else:
            # ── 本地文件路径分支 ──
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            filename = os.path.basename(image_path)

        # ── 公共检测逻辑（URL 和本地文件共用） ──
        db = SessionLocal()
        try:
            # 使用默认场景 ID=1（火灾烟雾检测场景）
            task = detection_service.detect_single(
                db=db,
                user_id=1,  # Agent 调用时使用系统默认用户
                scene_id=1,
                image_file=image_bytes,
                filename=filename,
                conf_threshold=conf,
                iou_threshold=iou,
            )

            # 如果检测任务失败，直接返回错误信息，避免伪装成“未检测到目标”
            if getattr(task, "status", None) == "failed":
                return json.dumps(
                    {"error": task.error_message or "图片检测失败，请稍后重试。"},
                    ensure_ascii=False,
                )

            # 查询检测结果详情（每个检测到的目标）
            detections = (
                db.query(DetectionResult)
                .filter(DetectionResult.task_id == task.id)
                .all()
            )

            # 构建检测结果摘要
            fire_count = task.fire_object_count or 0
            smoke_count = task.smoke_object_count or 0
            total_count = fire_count + smoke_count
            fire_level = task.fire_level or "unknown"
            inference_time = task.total_inference_time or 0

            result_lines = [f"检测完成！共发现 {total_count} 个目标："]
            detection_list = []
            for det in detections:
                class_cn = getattr(det, "class_name_cn", None) or det.class_name
                result_lines.append(f"- {class_cn}: 置信度 {det.confidence:.2f}")
                detection_list.append({
                    "class_name": det.class_name,
                    "class_name_cn": class_cn,
                    "confidence": float(det.confidence),
                    "bbox": det.bbox,
                })

            result_lines.append(f"推理耗时: {inference_time:.0f}ms")

            if fire_level in ("warning", "danger"):
                result_lines.append("⚠️ 警告：检测到火情，请立即关注并采取相应措施！")
            elif smoke_count > 0:
                result_lines.append("⚠️ 提示：检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 未检测到火焰或烟雾，当前状态安全。")

            summary = "\n".join(result_lines)

            # 优先使用 MinIO URL；若上传失败，使用 detection_service 附加的 base64 兜底
            annotated_image_url = task.annotated_url
            annotated_image_base64 = getattr(task, "annotated_image_base64", None)
            if not annotated_image_url and annotated_image_base64:
                try:
                    annotated_image_base64 = base64.b64encode(
                        base64.b64decode(annotated_image_base64)
                    ).decode("utf-8")
                except Exception:
                    logger.warning("标注图 base64 解码失败，将不返回该字段")
                    annotated_image_base64 = None

            result_payload = {
                "summary": summary,
                "annotated_image_url": annotated_image_url,
                "fire_object_count": fire_count,
                "smoke_object_count": smoke_count,
                "total_objects": total_count,
                "fire_level": fire_level,
                "inference_time": inference_time,
                "detections": detection_list,
                "original_image_url": task.original_url,
            }
            # 仅当 base64 非空时才返回，避免前端因空字段误判
            if annotated_image_base64:
                result_payload["annotated_image_base64"] = annotated_image_base64
            return json.dumps(result_payload, ensure_ascii=False)
        finally:
            db.close()
    except FileNotFoundError:
        return json.dumps({"error": f"找不到图片文件 '{image_path}'，请确认文件路径是否正确。"}, ensure_ascii=False)
    except Exception as e:
        logger.exception("单图检测工具调用失败: image_path=%s", image_path)
        return json.dumps({"error": f"单图检测失败：{str(e)}"}, ensure_ascii=False)


@tool
def detect_batch_images(
    image_paths: List[str],
    conf: float = 0.25,
) -> str:
    """对多张图片进行批量火焰烟雾检测。

    适用场景：用户需要一次性检测多张图片，如监控截图批量分析。

    Args:
        image_paths: 图片文件路径列表，每项为本地路径或 MinIO URL。
        conf: 置信度阈值（0.0~1.0），默认 0.25。

    Returns:
        str: 批量检测结果摘要，包含总检测数、检出火焰/烟雾的图片数、火情统计等。
    """
    try:
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            image_files_list: List[bytes] = []
            filenames_list: List[str] = []
            import os

            for path in image_paths:
                with open(path, "rb") as f:
                    image_files_list.append(f.read())
                filenames_list.append(os.path.basename(path))

            tasks = detection_service.detect_batch(
                db=db,
                user_id=1,
                scene_id=1,
                image_files=image_files_list,
                filenames=filenames_list,
                conf_threshold=conf,
            )

            total = len(tasks)
            fire_detected = sum(1 for t in tasks if (t.fire_object_count or 0) > 0)
            smoke_detected = sum(1 for t in tasks if (t.smoke_object_count or 0) > 0)
            warning_count = sum(1 for t in tasks if t.fire_level in ("warning", "danger"))

            result_lines = [
                f"【批量检测结果】",
                f"总检测图片数：{total}",
                f"检出火焰的图片：{fire_detected} 张",
                f"检出烟雾的图片：{smoke_detected} 张",
                f"触发预警的图片：{warning_count} 张",
            ]

            if warning_count > 0:
                result_lines.append("⚠️ 警告：部分图片检测到火情，请立即关注！")
            elif smoke_detected > 0:
                result_lines.append("⚠️ 提示：部分图片检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 所有图片均未检测到火焰或烟雾。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except Exception as e:
        logger.exception("批量检测工具调用失败")
        return f"批量检测失败：{str(e)}"


@tool
def detect_zip_images_file(
    zip_path: str,
    conf: float = 0.25,
) -> str:
    """对 ZIP 压缩包中的图片进行批量火焰烟雾检测。

    适用场景：用户上传 ZIP 压缩包，包含多张需要检测的图片。

    Args:
        zip_path: ZIP 压缩包文件的本地路径。
        conf: 置信度阈值（0.0~1.0），默认 0.25。

    Returns:
        str: ZIP 批量检测结果摘要，包含解压文件数、成功检测数、检出统计等。
    """
    try:
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        import os
        filename = os.path.basename(zip_path)

        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            tasks = detection_service.detect_zip(
                db=db,
                user_id=1,
                scene_id=1,
                zip_bytes=zip_bytes,
                filename=filename,
                conf_threshold=conf,
            )

            total = len(tasks)
            fire_detected = sum(1 for t in tasks if (t.fire_object_count or 0) > 0)
            smoke_detected = sum(1 for t in tasks if (t.smoke_object_count or 0) > 0)
            warning_count = sum(1 for t in tasks if t.fire_level in ("warning", "danger"))

            result_lines = [
                f"【ZIP 批量检测结果】",
                f"ZIP 文件：{filename}",
                f"成功检测图片数：{total}",
                f"检出火焰的图片：{fire_detected} 张",
                f"检出烟雾的图片：{smoke_detected} 张",
                f"触发预警的图片：{warning_count} 张",
            ]

            if warning_count > 0:
                result_lines.append("⚠️ 警告：ZIP 包中部分图片检测到火情，请立即关注！")
            elif smoke_detected > 0:
                result_lines.append("⚠️ 提示：ZIP 包中部分图片检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ ZIP 包中所有图片均未检测到火焰或烟雾。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except FileNotFoundError:
        return f"错误：找不到 ZIP 文件 '{zip_path}'，请确认文件路径是否正确。"
    except Exception as e:
        logger.exception("ZIP 批量检测工具调用失败: zip_path=%s", zip_path)
        return f"ZIP 批量检测失败：{str(e)}"


@tool
def detect_video_file(
    video_path: str,
    conf: float = 0.25,
    frame_sample_rate: int = 5,
) -> str:
    """对视频文件进行逐帧火焰烟雾检测。

    适用场景：用户上传监控视频，需要检测视频中是否出现火焰或烟雾。

    Args:
        video_path: 视频文件的本地路径。
        conf: 置信度阈值（0.0~1.0），默认 0.25。
        frame_sample_rate: 采样帧率，默认 5（即每 5 帧检测一次）。值越大检测越快，但可能遗漏短暂出现的火焰/烟雾。

    Returns:
        str: 视频检测结果摘要，包含视频时长、总帧数、检出火焰/烟雾的帧数、火情等级等。
    """
    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        import os
        filename = os.path.basename(video_path)

        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            task = detection_service.detect_video(
                db=db,
                user_id=1,
                scene_id=1,
                video_bytes=video_bytes,
                filename=filename,
                conf_threshold=conf,
                frame_skip=frame_sample_rate,
            )

            fire_count = task.fire_object_count or 0
            smoke_count = task.smoke_object_count or 0
            fire_level = task.fire_level or "unknown"
            duration = task.video_duration or 0

            result_lines = [
                f"【视频检测结果】",
                f"视频文件：{filename}",
                f"视频时长：{duration:.1f} 秒",
                f"检测类别：fire（火焰）× {fire_count}，smoke（烟雾）× {smoke_count}",
                f"火情等级：{fire_level}",
                f"采样帧率：每 {frame_sample_rate} 帧检测一次",
            ]

            if fire_level in ("warning", "danger"):
                result_lines.append("⚠️ 警告：视频中检测到火情，请立即关注并采取相应措施！")
            elif smoke_count > 0:
                result_lines.append("⚠️ 提示：视频中检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 视频中未检测到火焰或烟雾，当前状态安全。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except FileNotFoundError:
        return f"错误：找不到视频文件 '{video_path}'，请确认文件路径是否正确。"
    except Exception as e:
        logger.exception("视频检测工具调用失败: video_path=%s", video_path)
        return f"视频检测失败：{str(e)}"
```
**当前版本（缺失/被改）**：
```python
"""
检测工具封装模块

将 DetectionService 的 4 个核心检测方法封装为 LangChain @tool 装饰器工具，
供 ReAct Agent 在推理过程中调用。

检测类别：fire（火焰）、smoke（烟雾）
"""

from typing import List, Optional

from langchain_core.tools import tool

from app.services.detection_service import detection_service
from app.core.logger import get_logger

logger = get_logger(__name__)


@tool
def detect_single_image(
    image_path: str,
    conf: float = 0.25,
    iou: float = 0.45,
) -> str:
    """对单张图片进行火焰和烟雾目标检测。

    适用场景：用户上传单张图片，需要检测其中是否存在火焰或烟雾。

    Args:
        image_path: 图片文件的本地路径或 MinIO URL。
        conf: 置信度阈值（0.0~1.0），默认 0.25。低于此值的检测结果会被过滤。
        iou: NMS（非极大值抑制）IoU 阈值（0.0~1.0），默认 0.45。用于去除重叠框。

    Returns:
        str: 检测结果摘要，包含检测到的火焰/烟雾目标数量、置信度、火情等级等信息。
    """
    import os
    import tempfile

    # 标记是否为 URL 下载的临时文件（用于后续清理）
    _tmp_file_path = None

    try:
        # ── URL 检测分支：如果 image_path 是 HTTP/HTTPS URL，先下载到临时文件 ──
        if image_path.startswith(("http://", "https://")):
            logger.info("检测到 URL 图片，开始下载: %s", image_path)
            import requests
            try:
                response = requests.get(image_path, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                return f"错误：无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"

            # 将下载的图片写入临时文件（保留 .jpg 后缀以便 OpenCV 正确解码）
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(response.content)
                _tmp_file_path = tmp.name

            # 从临时文件读取图片字节
            with open(_tmp_file_path, "rb") as f:
                image_bytes = f.read()

            # 从 URL 中提取文件名
            filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
            logger.info("URL 图片下载成功，临时文件: %s, 大小: %d bytes", _tmp_file_path, len(image_bytes))
        else:
            # ── 原有本地文件路径分支 ──
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            filename = os.path.basename(image_path)

        # ── 公共检测逻辑（URL 和本地文件共用） ──
        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            # 使用默认场景 ID=1（火灾烟雾检测场景）
            task = detection_service.detect_single(
                db=db,
                user_id=1,  # Agent 调用时使用系统默认用户
                scene_id=1,
                image_file=image_bytes,
                filename=filename,
                conf_threshold=conf,
                iou_threshold=iou,
            )

            # 查询检测结果详情（每个检测到的目标）
            from app.entity.db_models import DetectionResult
            detections = (
                db.query(DetectionResult)
                .filter(DetectionResult.task_id == task.id)
                .all()
            )

            # 构建检测结果摘要
            fire_count = task.fire_object_count or 0
            smoke_count = task.smoke_object_count or 0
            total_count = fire_count + smoke_count
            fire_level = task.fire_level or "unknown"
            inference_time = task.total_inference_time or 0

            result_lines = [
                f"检测完成！共发现 {total_count} 个目标：",
            ]

            # 逐条列出检测到的目标及置信度
            for det in detections:
                class_cn = getattr(det, "class_name_cn", None) or det.class_name
                result_lines.append(f"- {class_cn}: 置信度 {det.confidence:.2f}")

            result_lines.append(f"推理耗时: {inference_time:.0f}ms")

            if fire_level in ("warning", "danger"):
                result_lines.append("⚠️ 警告：检测到火情，请立即关注并采取相应措施！")
            elif smoke_count > 0:
                result_lines.append("⚠️ 提示：检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 未检测到火焰或烟雾，当前状态安全。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except FileNotFoundError:
        return f"错误：找不到图片文件 '{image_path}'，请确认文件路径是否正确。"
    except Exception as e:
        logger.exception("单图检测工具调用失败: image_path=%s", image_path)
        return f"单图检测失败：{str(e)}"
    finally:
        # 清理 URL 下载产生的临时文件
        if _tmp_file_path and os.path.exists(_tmp_file_path):
            try:
                os.unlink(_tmp_file_path)
                logger.info("已清理临时文件: %s", _tmp_file_path)
            except Exception:
                pass


@tool
def detect_batch_images(
    image_paths: List[str],
    conf: float = 0.25,
) -> str:
    """对多张图片进行批量火焰烟雾检测。

    适用场景：用户需要一次性检测多张图片，如监控截图批量分析。

    Args:
        image_paths: 图片文件路径列表，每项为本地路径或 MinIO URL。
        conf: 置信度阈值（0.0~1.0），默认 0.25。

    Returns:
        str: 批量检测结果摘要，包含总检测数、检出火焰/烟雾的图片数、火情统计等。
    """
    try:
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            image_files_list: List[bytes] = []
            filenames_list: List[str] = []
            import os

            for path in image_paths:
                with open(path, "rb") as f:
                    image_files_list.append(f.read())
                filenames_list.append(os.path.basename(path))

            tasks = detection_service.detect_batch(
                db=db,
                user_id=1,
                scene_id=1,
                image_files=image_files_list,
                filenames=filenames_list,
                conf_threshold=conf,
            )

            total = len(tasks)
            fire_detected = sum(1 for t in tasks if (t.fire_object_count or 0) > 0)
            smoke_detected = sum(1 for t in tasks if (t.smoke_object_count or 0) > 0)
            warning_count = sum(1 for t in tasks if t.fire_level in ("warning", "danger"))

            result_lines = [
                f"【批量检测结果】",
                f"总检测图片数：{total}",
                f"检出火焰的图片：{fire_detected} 张",
                f"检出烟雾的图片：{smoke_detected} 张",
                f"触发预警的图片：{warning_count} 张",
            ]

            if warning_count > 0:
                result_lines.append("⚠️ 警告：部分图片检测到火情，请立即关注！")
            elif smoke_detected > 0:
                result_lines.append("⚠️ 提示：部分图片检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 所有图片均未检测到火焰或烟雾。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except Exception as e:
        logger.exception("批量检测工具调用失败")
        return f"批量检测失败：{str(e)}"


@tool
def detect_zip_images_file(
    zip_path: str,
    conf: float = 0.25,
) -> str:
    """对 ZIP 压缩包中的图片进行批量火焰烟雾检测。

    适用场景：用户上传 ZIP 压缩包，包含多张需要检测的图片。

    Args:
        zip_path: ZIP 压缩包文件的本地路径。
        conf: 置信度阈值（0.0~1.0），默认 0.25。

    Returns:
        str: ZIP 批量检测结果摘要，包含解压文件数、成功检测数、检出统计等。
    """
    try:
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        import os
        filename = os.path.basename(zip_path)

        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            tasks = detection_service.detect_zip(
                db=db,
                user_id=1,
                scene_id=1,
                zip_bytes=zip_bytes,
                filename=filename,
                conf_threshold=conf,
            )

            total = len(tasks)
            fire_detected = sum(1 for t in tasks if (t.fire_object_count or 0) > 0)
            smoke_detected = sum(1 for t in tasks if (t.smoke_object_count or 0) > 0)
            warning_count = sum(1 for t in tasks if t.fire_level in ("warning", "danger"))

            result_lines = [
                f"【ZIP 批量检测结果】",
                f"ZIP 文件：{filename}",
                f"成功检测图片数：{total}",
                f"检出火焰的图片：{fire_detected} 张",
                f"检出烟雾的图片：{smoke_detected} 张",
                f"触发预警的图片：{warning_count} 张",
            ]

            if warning_count > 0:
                result_lines.append("⚠️ 警告：ZIP 包中部分图片检测到火情，请立即关注！")
            elif smoke_detected > 0:
                result_lines.append("⚠️ 提示：ZIP 包中部分图片检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ ZIP 包中所有图片均未检测到火焰或烟雾。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except FileNotFoundError:
        return f"错误：找不到 ZIP 文件 '{zip_path}'，请确认文件路径是否正确。"
    except Exception as e:
        logger.exception("ZIP 批量检测工具调用失败: zip_path=%s", zip_path)
        return f"ZIP 批量检测失败：{str(e)}"


@tool
def detect_video_file(
    video_path: str,
    conf: float = 0.25,
    frame_sample_rate: int = 5,
) -> str:
    """对视频文件进行逐帧火焰烟雾检测。

    适用场景：用户上传监控视频，需要检测视频中是否出现火焰或烟雾。

    Args:
        video_path: 视频文件的本地路径。
        conf: 置信度阈值（0.0~1.0），默认 0.25。
        frame_sample_rate: 采样帧率，默认 5（即每 5 帧检测一次）。值越大检测越快，但可能遗漏短暂出现的火焰/烟雾。

    Returns:
        str: 视频检测结果摘要，包含视频时长、总帧数、检出火焰/烟雾的帧数、火情等级等。
    """
    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        import os
        filename = os.path.basename(video_path)

        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            task = detection_service.detect_video(
                db=db,
                user_id=1,
                scene_id=1,
                video_bytes=video_bytes,
                filename=filename,
                conf_threshold=conf,
                frame_skip=frame_sample_rate,
            )

            fire_count = task.fire_object_count or 0
            smoke_count = task.smoke_object_count or 0
            fire_level = task.fire_level or "unknown"
            duration = task.video_duration or 0

            result_lines = [
                f"【视频检测结果】",
                f"视频文件：{filename}",
                f"视频时长：{duration:.1f} 秒",
                f"检测类别：fire（火焰）× {fire_count}，smoke（烟雾）× {smoke_count}",
                f"火情等级：{fire_level}",
                f"采样帧率：每 {frame_sample_rate} 帧检测一次",
            ]

            if fire_level in ("warning", "danger"):
                result_lines.append("⚠️ 警告：视频中检测到火情，请立即关注并采取相应措施！")
            elif smoke_count > 0:
                result_lines.append("⚠️ 提示：视频中检测到烟雾，建议持续关注。")
            else:
                result_lines.append("✅ 视频中未检测到火焰或烟雾，当前状态安全。")

            return "\n".join(result_lines)
        finally:
            db.close()
    except FileNotFoundError:
        return f"错误：找不到视频文件 '{video_path}'，请确认文件路径是否正确。"
    except Exception as e:
        logger.exception("视频检测工具调用失败: video_path=%s", video_path)
        return f"视频检测失败：{str(e)}"
```
**统一差异（unified diff）**：
```diff
--- backup/backend/app/agent/tools/detection_tool.py
+++ current/backend/app/agent/tools/detection_tool.py
@@ -7,15 +7,10 @@
 检测类别：fire（火焰）、smoke（烟雾）
 """
 
-import base64
-import json
-import os
 from typing import List, Optional
 
 from langchain_core.tools import tool
 
-from app.database.session import SessionLocal
-from app.entity.db_models import DetectionResult
 from app.services.detection_service import detection_service
 from app.core.logger import get_logger
 
@@ -38,61 +33,45 @@
         iou: NMS（非极大值抑制）IoU 阈值（0.0~1.0），默认 0.45。用于去除重叠框。
 
     Returns:
-        str: JSON 格式的检测结果，包含文字摘要、标注图 URL/base64、检测框列表等。
+        str: 检测结果摘要，包含检测到的火焰/烟雾目标数量、置信度、火情等级等信息。
     """
-    if not image_path:
-        return json.dumps({"error": "图片路径为空，请提供有效的图片路径或 URL。"}, ensure_ascii=False)
+    import os
+    import tempfile
+
+    # 标记是否为 URL 下载的临时文件（用于后续清理）
+    _tmp_file_path = None
 
     try:
-        # ── URL 检测分支：如果 image_path 是 HTTP/HTTPS URL，先下载到内存 ──
+        # ── URL 检测分支：如果 image_path 是 HTTP/HTTPS URL，先下载到临时文件 ──
         if image_path.startswith(("http://", "https://")):
             logger.info("检测到 URL 图片，开始下载: %s", image_path)
-            from urllib.parse import urlparse
-
-            # 判断是否为 MinIO 预签名 URL，若是则直接用 MinIO 客户端下载（避免 403）
-            from app.storage.minio_client import MinIOClient
-            parsed = urlparse(image_path)
-            # 从 URL 路径中提取对象名称：/bucket-name/object/path → object/path
-            path_parts = parsed.path.lstrip("/").split("/", 1)
-            if len(path_parts) > 1:
-                object_name = path_parts[1].split("?")[0]  # 去掉查询参数
-                try:
-                    minio = MinIOClient()
-                    stream = minio.get_file_stream(minio.bucket_name, object_name)
-                    image_bytes = stream.read()
-                    stream.close()
-                    filename = os.path.basename(object_name) or "downloaded_image.jpg"
-                    logger.info("通过 MinIO 客户端下载成功: %s, 大小: %d bytes", object_name, len(image_bytes))
-                except Exception as minio_err:
-                    # MinIO 客户端下载失败，回退到 HTTP 下载
-                    logger.warning("MinIO 客户端下载失败，回退到 HTTP: %s", minio_err)
-                    import requests
-                    try:
-                        response = requests.get(image_path, timeout=30)
-                        response.raise_for_status()
-                        image_bytes = response.content
-                        filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
-                        logger.info("HTTP 下载成功，大小: %d bytes", len(image_bytes))
-                    except requests.RequestException as e:
-                        return json.dumps({"error": f"无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"}, ensure_ascii=False)
-            else:
-                # 非 MinIO URL，用 HTTP 下载
-                import requests
-                try:
-                    response = requests.get(image_path, timeout=30)
-                    response.raise_for_status()
-                    image_bytes = response.content
-                    filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
-                    logger.info("HTTP 下载成功，大小: %d bytes", len(image_bytes))
-                except requests.RequestException as e:
-                    return json.dumps({"error": f"无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"}, ensure_ascii=False)
+            import requests
+            try:
+                response = requests.get(image_path, timeout=30)
+                response.raise_for_status()
+            except requests.RequestException as e:
+                return f"错误：无法下载图片 '{image_path}'，请确认 URL 是否可访问。（{str(e)}）"
+
+            # 将下载的图片写入临时文件（保留 .jpg 后缀以便 OpenCV 正确解码）
+            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
+                tmp.write(response.content)
+                _tmp_file_path = tmp.name
+
+            # 从临时文件读取图片字节
+            with open(_tmp_file_path, "rb") as f:
+                image_bytes = f.read()
+
+            # 从 URL 中提取文件名
+            filename = os.path.basename(image_path.split("?")[0]) or "downloaded_image.jpg"
+            logger.info("URL 图片下载成功，临时文件: %s, 大小: %d bytes", _tmp_file_path, len(image_bytes))
         else:
-            # ── 本地文件路径分支 ──
+            # ── 原有本地文件路径分支 ──
             with open(image_path, "rb") as f:
                 image_bytes = f.read()
             filename = os.path.basename(image_path)
 
         # ── 公共检测逻辑（URL 和本地文件共用） ──
+        from app.database.session import SessionLocal
         db = SessionLocal()
         try:
             # 使用默认场景 ID=1（火灾烟雾检测场景）
@@ -106,14 +85,8 @@
                 iou_threshold=iou,
             )
 
-            # 如果检测任务失败，直接返回错误信息，避免伪装成“未检测到目标”
-            if getattr(task, "status", None) == "failed":
-                return json.dumps(
-                    {"error": task.error_message or "图片检测失败，请稍后重试。"},
-                    ensure_ascii=False,
-                )
-
             # 查询检测结果详情（每个检测到的目标）
+            from app.entity.db_models import DetectionResult
             detections = (
                 db.query(DetectionResult)
                 .filter(DetectionResult.task_id == task.id)
@@ -127,17 +100,14 @@
             fire_level = task.fire_level or "unknown"
             inference_time = task.total_inference_time or 0
 
-            result_lines = [f"检测完成！共发现 {total_count} 个目标："]
-            detection_list = []
+            result_lines = [
+                f"检测完成！共发现 {total_count} 个目标：",
+            ]
+
+            # 逐条列出检测到的目标及置信度
             for det in detections:
                 class_cn = getattr(det, "class_name_cn", None) or det.class_name
                 result_lines.append(f"- {class_cn}: 置信度 {det.confidence:.2f}")
-                detection_list.append({
-                    "class_name": det.class_name,
-                    "class_name_cn": class_cn,
-                    "confidence": float(det.confidence),
-                    "bbox": det.bbox,
-                })
 
             result_lines.append(f"推理耗时: {inference_time:.0f}ms")
 
@@ -148,42 +118,22 @@
             else:
                 result_lines.append("✅ 未检测到火焰或烟雾，当前状态安全。")
 
-            summary = "\n".join(result_lines)
-
-            # 优先使用 MinIO URL；若上传失败，使用 detection_service 附加的 base64 兜底
-            annotated_image_url = task.annotated_url
-            annotated_image_base64 = getattr(task, "annotated_image_base64", None)
-            if not annotated_image_url and annotated_image_base64:
-                try:
-                    annotated_image_base64 = base64.b64encode(
-                        base64.b64decode(annotated_image_base64)
-                    ).decode("utf-8")
-                except Exception:
-                    logger.warning("标注图 base64 解码失败，将不返回该字段")
-                    annotated_image_base64 = None
-
-            result_payload = {
-                "summary": summary,
-                "annotated_image_url": annotated_image_url,
-                "fire_object_count": fire_count,
-                "smoke_object_count": smoke_count,
-                "total_objects": total_count,
-                "fire_level": fire_level,
-                "inference_time": inference_time,
-                "detections": detection_list,
-                "original_image_url": task.original_url,
-            }
-            # 仅当 base64 非空时才返回，避免前端因空字段误判
-            if annotated_image_base64:
-                result_payload["annotated_image_base64"] = annotated_image_base64
-            return json.dumps(result_payload, ensure_ascii=False)
+            return "\n".join(result_lines)
         finally:
             db.close()
     except FileNotFoundError:
-        return json.dumps({"error": f"找不到图片文件 '{image_path}'，请确认文件路径是否正确。"}, ensure_ascii=False)
+        return f"错误：找不到图片文件 '{image_path}'，请确认文件路径是否正确。"
     except Exception as e:
         logger.exception("单图检测工具调用失败: image_path=%s", image_path)
-        return json.dumps({"error": f"单图检测失败：{str(e)}"}, ensure_ascii=False)
+        return f"单图检测失败：{str(e)}"
+    finally:
+        # 清理 URL 下载产生的临时文件
+        if _tmp_file_path and os.path.exists(_tmp_file_path):
+            try:
+                os.unlink(_tmp_file_path)
+                logger.info("已清理临时文件: %s", _tmp_file_path)
+            except Exception:
+                pass
 
 
 @tool
```
**结论**：恢复 JSON 格式返回，包含 annotated_image_base64、detections 数组、error 字段等。


---

### 文件：backend/app/services/chat_service.py
**优先级**：P0
**影响说明**：智能对话服务核心逻辑变化，影响 SSE 事件格式、图片预处理、真实 LLM 调用、错误处理与对话历史。
**备份版本（原功能）**：
```python
"""
对话服务
处理 Agent/Chat 会话和消息的 CRUD 业务逻辑

集成 ReAct Agent：
- LLM_STUB_MODE=true 时：使用占位逻辑，模拟 Agent 思考→工具调用→回复的流程
- LLM_STUB_MODE=false 时：使用真实的 LangChain ChatOpenAI + ReAct Agent
"""

import asyncio
import concurrent.futures
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agent.detection_agent import detection_agent
from app.entity.db_models import ChatSession, ChatMessage
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """对话服务，集成 ReAct Agent 实现智能火灾烟雾检测对话"""

    # ── 工具名称到意图关键词的映射（用于 Stub 模式下的意图识别） ──
    _TOOL_INTENT_MAP = {
        "detect_single_image": {
            "keywords": ["检测", "识别", "图片", "图像", "照片", "单张", "单图", "这张"],
            "description": "单图火焰烟雾检测",
        },
        "detect_batch_images": {
            "keywords": ["批量", "多张", "多图", "一组", "这些图片", "批量检测"],
            "description": "批量图片检测",
        },
        "detect_zip_images_file": {
            "keywords": ["zip", "压缩包", "打包", "压缩文件", "解压"],
            "description": "ZIP 压缩包检测",
        },
        "detect_video_file": {
            "keywords": ["视频", "录像", "监控", "mp4", "avi", "摄像头"],
            "description": "视频检测",
        },
        "search_knowledge": {
            "keywords": ["知识", "原理", "怎么", "如何", "为什么", "什么", "介绍", "说明", "解释", "特点", "应用"],
            "description": "知识检索",
        },
        "query_detection_stats": {
            "keywords": ["统计", "概览", "总览", "数据", "统计数", "统计概览", "整体情况"],
            "description": "统计查询",
        },
        "query_detection_history": {
            "keywords": ["历史", "记录", "历史记录", "检测记录", "最近", "之前"],
            "description": "历史查询",
        },
        "query_user_list": {
            "keywords": ["用户", "人员", "账号", "成员", "用户列表", "谁"],
            "description": "用户查询",
        },
    }

    # ══════════════════════════════════════════════════════════════
    # 会话管理方法（保持不变）
    # ══════════════════════════════════════════════════════════════

    def create_session(self, db: Session, user_id: int, title: Optional[str] = None) -> ChatSession:
        """
        创建对话会话
        Args:
            db: 数据库会话
            user_id: 用户 ID
            title: 会话标题（可选，默认"新对话"）
        Returns:
            新创建的会话对象
        """
        session_uuid = str(uuid.uuid4())
        chat_session = ChatSession(
            user_id=user_id,
            session_uuid=session_uuid,
            title=title or "新对话",
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        logger.info(f"创建会话成功: user_id={user_id}, uuid={session_uuid}")
        return chat_session

    def get_sessions(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """获取用户会话列表（分页）"""
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
        total = query.count()
        sessions = (
            query.order_by(desc(ChatSession.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "id": s.id,
                    "session_uuid": s.session_uuid,
                    "title": s.title,
                    "status": s.status,
                    "message_count": s.message_count,
                    "last_message_at": s.last_message_at,
                    "created_at": s.created_at,
                }
                for s in sessions
            ],
        }

    def get_session_messages(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> list[dict]:
        """获取会话消息历史"""
        self._get_user_session(db, session_id, user_id)
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "agent_used": m.agent_used,
                "tool_calls": m.tool_calls,
                "tool_result": m.tool_result,
                "tokens_used": m.tokens_used,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    def send_message(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        content: str,
        files: list = None,
    ) -> dict:
        """
        发送消息并存储（集成 ReAct Agent 流程）
        Args:
            db: 数据库会话
            session_id: 会话 ID
            user_id: 用户 ID
            content: 消息内容
            files: 上传的文件列表（可选）
        Returns:
            包含 user_message 和 assistant_message 的字典
        """
        session = self._get_user_session(db, session_id, user_id)

        # 构建存储到数据库的消息内容（包含图片 URL 信息，用于多轮对话记忆）
        stored_content = content
        if files:
            file_hints = []
            for f in files:
                file_type = f.get("type", "file")
                file_url = f.get("url", "")
                file_name = f.get("name", "")
                if file_type == "image":
                    file_hints.append(f"[用户上传了图片: {file_url}]")
                elif file_type == "zip":
                    file_hints.append(f"[用户上传了ZIP压缩包: {file_url}]")
                elif file_type == "video":
                    file_hints.append(f"[用户上传了视频: {file_url}]")
                else:
                    file_hints.append(f"[用户上传了文件: {file_url} ({file_name})]")
            if file_hints:
                stored_content = "\n".join(file_hints) + "\n" + content

        # 存储用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=stored_content,
        )
        db.add(user_msg)
        db.flush()

        # 加载会话历史作为 LLM 上下文
        history_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

        # AI 回复（通过 Agent 流程生成）
        reply_content, tool_calls, tool_result, tokens_used, latency_ms = self._run_agent(
            content, history=history, files=files
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply_content,
            agent_used="react_agent",
            tool_calls=tool_calls if tool_calls else None,
            tool_result=tool_result if tool_result else None,
            tokens_used=tokens_used if tokens_used > 0 else None,
            latency_ms=latency_ms if latency_ms > 0 else None,
        )
        db.add(assistant_msg)

        # 更新会话信息
        session.message_count = (session.message_count or 0) + 2
        session.last_message_at = datetime.now(timezone.utc)
        if session.message_count == 2:
            session.title = content[:50] if len(content) > 50 else content

        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return {
            "user_message": {
                "id": user_msg.id,
                "session_id": user_msg.session_id,
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at,
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "session_id": assistant_msg.session_id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "agent_used": assistant_msg.agent_used,
                "tool_calls": assistant_msg.tool_calls,
                "tool_result": assistant_msg.tool_result,
                "created_at": assistant_msg.created_at,
            },
        }

    def delete_session(self, db: Session, session_id: int, user_id: int) -> bool:
        """删除会话（含消息级联删除）"""
        session = self._get_user_session(db, session_id, user_id)
        db.delete(session)
        db.commit()
        logger.info(f"删除会话成功: session_id={session_id}, user_id={user_id}")
        return True

    def _get_user_session(self, db: Session, session_id: int, user_id: int) -> ChatSession:
        """获取用户所属会话（验证权限）"""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        return session

    # ══════════════════════════════════════════════════════════════
    # Agent 核心逻辑
    # ══════════════════════════════════════════════════════════════

    def _run_agent(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        运行 Agent 流程，生成回复。

        根据 LLM_STUB_MODE 配置选择不同的执行路径：
        - True：使用占位模拟流程（不依赖外部 LLM API）
        - False：使用真实的 LangChain ReAct Agent

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表

        Returns:
            tuple: (回复内容, tool_calls列表, tool_result字符串, token数, 延迟毫秒数)
        """
        if settings.LLM_STUB_MODE:
            return self._run_agent_stub(content, history, files)
        else:
            return self._run_agent_real(content, history, files)

    def _run_agent_stub(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        Stub 模式：模拟 ReAct Agent 的思考→工具调用→回复流程。

        流程：
        1. 意图识别：根据关键词匹配确定用户意图
        2. 工具调用：模拟 Agent 选择合适的工具并执行
        3. 结果汇总：将工具返回结果格式化为自然语言回复

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表，每个文件包含 url/type/name 字段
        """
        start_time = time.time()
        tool_calls = []
        tool_result = ""

        normalized = content.strip()

        # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
        if files and self._has_image_file(files):
            has_detect_keyword = any(
                kw in normalized for kw in ["检测", "识别", "看看", "分析"]
            )
            if has_detect_keyword or not normalized:
                # 提取第一个图片 URL
                image_url = self._extract_first_image_url(files)
                if image_url:
                    tool_name = "detect_single_image"
                    tool_args = {"image_path": image_url}
                    tool_calls = [{"tool": tool_name, "args": tool_args}]

                    logger.info(
                        "Agent Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                        image_url,
                    )

                    try:
                        tool_result = self._invoke_tool_stub(tool_name, tool_args)
                    except Exception as e:
                        logger.exception("Agent Stub 图片检测工具调用失败: %s", e)
                        tool_result = f"工具调用失败：{str(e)}"

                    reply = self._format_agent_response(
                        user_message=normalized,
                        tool_name=tool_name,
                        tool_description="单图火焰烟雾检测",
                        tool_result=tool_result,
                    )

                    latency_ms = int((time.time() - start_time) * 1000)
                    tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)
                    return reply, tool_calls, tool_result, tokens_used, latency_ms

        # ── 步骤 1：意图识别 ──
        # 根据关键词匹配，找到最可能的工具意图
        matched_tool = self._match_intent(normalized)

        # ── 步骤 2：工具调用（模拟） ──
        if matched_tool:
            tool_name = matched_tool["name"]
            tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
            tool_calls = [{"tool": tool_name, "args": tool_args}]

            logger.info(
                "Agent Stub: 意图=%s, 工具=%s, 参数=%s",
                matched_tool["description"], tool_name, tool_args,
            )

            try:
                tool_result = self._invoke_tool_stub(tool_name, tool_args)
            except Exception as e:
                logger.exception("Agent Stub 工具调用失败: tool=%s", tool_name)
                tool_result = f"工具调用失败：{str(e)}"

            # ── 步骤 3：生成自然语言回复 ──
            reply = self._format_agent_response(
                user_message=normalized,
                tool_name=tool_name,
                tool_description=matched_tool["description"],
                tool_result=tool_result,
            )
        else:
            # 无法匹配到具体工具，使用通用回复
            reply = self._build_stub_reply(normalized, history)

        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)

        return reply, tool_calls, tool_result, tokens_used, latency_ms

    def _run_agent_real(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        真实模式：复用 DetectionAgent 单例执行对话。

        DetectionAgent 已在 detection_agent.py 中根据 settings 完成 LLM 配置，
        这里直接调用其 chat() 方法，避免重复创建 LLM 和 AgentExecutor 实例。

        如果用户上传了图片，会先在函数内调用检测工具获取完整结果，再把文字摘要
        注入提示词交给 Agent，避免把 base64 标注图送入 LLM 上下文导致 token 超限。
        """
        start_time = time.time()
        tool_calls = []
        tool_result_str = ""

        try:
            if not detection_agent.available:
                raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

            # 若用户上传图片，先直接检测并把摘要注入提示词
            if files and self._has_image_file(files):
                first_image_url = self._extract_first_image_url(files)
                if first_image_url:
                    tool_name = "detect_single_image"
                    tool_args = {"image_path": first_image_url, "conf": 0.25, "iou": 0.45}
                    tool_calls.append({"tool": tool_name, "args": tool_args})

                    try:
                        from app.agent.tools.detection_tool import detect_single_image
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            tool_result_str = executor.submit(
                                detect_single_image.invoke, tool_args
                            ).result()
                    except Exception as e:
                        logger.exception("真实模式图片预处理检测失败")
                        tool_result_str = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                    display_text = self._extract_tool_result_summary(tool_name, tool_result_str)
                    content = (
                        f"{content}\n\n【系统提示】已对用户上传的图片完成火灾烟雾检测，"
                        f"检测结果摘要如下（请不要再次调用检测工具）：\n{display_text}\n"
                        f"请直接基于以上结果回复用户。"
                    )

            # 调用 detection_agent.chat()（异步 → 同步）
            result = asyncio.run(detection_agent.chat(content, history))

            reply_content = result.get("output", "抱歉，无法处理您的请求。")

            # 提取工具调用信息（Agent 可能基于系统提示不再调用检测工具）
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                action, observation = step
                # 仅记录非检测类工具的调用，避免重复记录已预处理的图片检测
                if action.tool != "detect_single_image":
                    tool_calls.append({
                        "tool": action.tool,
                        "args": action.tool_input,
                    })
                    if isinstance(observation, str):
                        tool_result_str += observation + "\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(content) + len(reply_content) + len(tool_result_str)) // 2)

            return reply_content, tool_calls, tool_result_str.strip(), tokens_used, latency_ms

        except Exception as e:
            logger.exception("ReAct Agent 执行失败")
            reply = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
            latency_ms = int((time.time() - start_time) * 1000)
            return reply, tool_calls, tool_result_str.strip(), 0, latency_ms

    # ══════════════════════════════════════════════════════════════
    # Stub 模式辅助方法
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _has_image_file(files: list) -> bool:
        """检查文件列表中是否包含图片类型文件"""
        if not files:
            return False
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                return True
        return False

    @staticmethod
    def _extract_first_image_url(files: list) -> Optional[str]:
        """从文件列表中提取第一个图片文件的 URL"""
        if not files:
            return None
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                url = f.get("url") or f.get("data", {}).get("url", "")
                if url:
                    return url
        return None

    def _match_intent(self, content: str) -> Optional[dict]:
        """
        根据用户消息内容匹配最可能的工具意图。

        使用关键词匹配 + 得分排序，找到最匹配的工具。

        Args:
            content: 用户消息内容

        Returns:
            dict 或 None: 匹配到的工具信息 {"name": ..., "description": ...}
        """
        content_lower = content.lower()
        best_score = 0
        best_tool = None

        for tool_name, info in self._TOOL_INTENT_MAP.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword.lower() in content_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_tool = {"name": tool_name, "description": info["description"]}

        return best_tool if best_score > 0 else None

    def _extract_tool_args_from_stub(self, content: str, tool_name: str) -> dict:
        """
        从用户消息中提取工具调用参数（Stub 模式下的简单参数提取）。

        使用正则表达式提取常见参数模式。

        Args:
            content: 用户消息内容
            tool_name: 匹配到的工具名称

        Returns:
            dict: 工具参数字典
        """
        args = {}

        # 提取置信度参数（如 "置信度 0.5"、"conf=0.3"）
        conf_match = re.search(r'(?:置信度|conf(?:idence)?)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if conf_match:
            args["conf"] = float(conf_match.group(1))

        # 提取帧率参数（如 "每5帧"、"采样率10"、"帧率3"）
        frame_match = re.search(r'(?:每\s*(\d+)\s*帧|采样率[=：:\s]*(\d+)|帧率[=：:\s]*(\d+))', content)
        if frame_match:
            frame_val = next(v for v in frame_match.groups() if v is not None)
            args["frame_sample_rate"] = int(frame_val)

        # 提取 IoU 参数
        iou_match = re.search(r'(?:iou|nms)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if iou_match:
            args["iou"] = float(iou_match.group(1))

        # 提取文件路径（简单模式：匹配常见的文件路径格式）
        path_match = re.search(r'(?:路径|文件|图片|视频|zip)[=：:\s]*([^\s,，。]+\.(?:jpg|jpeg|png|bmp|mp4|avi|zip))', content, re.IGNORECASE)
        if path_match:
            path_val = path_match.group(1)
            if tool_name in ("detect_single_image",):
                args["image_path"] = path_val
            elif tool_name == "detect_video_file":
                args["video_path"] = path_val
            elif tool_name == "detect_zip_images_file":
                args["zip_path"] = path_val

        # 提取页码
        page_match = re.search(r'(?:第\s*(\d+)\s*页|page[=：:\s]*(\d+))', content, re.IGNORECASE)
        if page_match:
            page_val = next(v for v in page_match.groups() if v is not None)
            args["page"] = int(page_val)

        return args

    def _invoke_tool_stub(self, tool_name: str, args: dict) -> str:
        """
        在 Stub 模式下调用工具（直接调用工具函数，不经过 LLM）。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            str: 工具返回结果
        """
        from app.agent.tools.detection_tool import (
            detect_single_image,
            detect_batch_images,
            detect_zip_images_file,
            detect_video_file,
        )
        from app.agent.tools.knowledge_tool import search_knowledge
        from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
        from app.agent.tools.user_tool import query_user_list

        tool_map = {
            "detect_single_image": detect_single_image,
            "detect_batch_images": detect_batch_images,
            "detect_zip_images_file": detect_zip_images_file,
            "detect_video_file": detect_video_file,
            "search_knowledge": search_knowledge,
            "query_detection_stats": query_detection_stats,
            "query_detection_history": query_detection_history,
            "query_user_list": query_user_list,
        }

        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return f"未知工具：{tool_name}"

        # 调用工具（LangChain @tool 装饰的函数可以直接调用）
        return tool_func.invoke(args)

    def _format_agent_response(
        self,
        user_message: str,
        tool_name: str,
        tool_description: str,
        tool_result: str,
    ) -> str:
        """
        将工具调用结果格式化为自然语言回复。

        模拟 Agent 在获得工具结果后，生成用户友好的回复。
        如果 tool_result 是 detect_single_image 返回的 JSON，则提取 summary 字段展示。

        Args:
            user_message: 用户原始消息
            tool_name: 使用的工具名称
            tool_description: 工具描述
            tool_result: 工具返回的结果

        Returns:
            str: 格式化的自然语言回复
        """
        # 根据工具类型生成不同的回复前缀
        prefixes = {
            "detect_single_image": "已为您完成单图火焰烟雾检测，以下是检测结果：",
            "detect_batch_images": "已为您完成批量图片火焰烟雾检测，以下是检测结果：",
            "detect_zip_images_file": "已为您完成 ZIP 压缩包中图片的火焰烟雾检测，以下是检测结果：",
            "detect_video_file": "已为您完成视频火焰烟雾检测，以下是检测结果：",
            "search_knowledge": "已为您检索火灾烟雾检测相关知识，以下是检索结果：",
            "query_detection_stats": "已为您查询检测统计概览，以下是统计数据：",
            "query_detection_history": "已为您查询检测历史记录，以下是历史记录：",
            "query_user_list": "已为您查询系统用户列表，以下是用户信息：",
        }

        prefix = prefixes.get(tool_name, f"已为您执行{tool_description}，以下是结果：")

        # 检测工具返回 JSON 时，优先展示 summary 文字，避免把 base64 输出到聊天正文
        display_result = tool_result
        if tool_name == "detect_single_image":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "summary" in parsed:
                    display_result = parsed["summary"]
            except json.JSONDecodeError:
                pass

        return f"{prefix}\n\n{display_result}"

    @staticmethod
    def _extract_tool_result_summary(tool_name: str, tool_result: str) -> str:
        """
        从工具结果中提取适合在聊天正文中展示的文字摘要。

        对于 detect_single_image 返回的 JSON，提取 summary 字段，
        避免将 base64 图片数据输出到聊天流中。
        """
        if tool_name == "detect_single_image":
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "summary" in parsed:
                    return parsed["summary"]
            except json.JSONDecodeError:
                pass
        return tool_result

    @staticmethod
    def _build_stub_reply(content: str, history: list = None) -> str:
        """
        根据输入生成确定性的本地占位回复，不访问任何外部大模型服务。

        当无法匹配到具体工具意图时，使用此方法生成通用回复。
        """
        normalized = content.strip()
        if any(keyword in normalized for keyword in ("火", "烟", "告警", "检测")):
            return (
                "这是本地占位回复：已收到火灾烟雾检测相关问题。\n"
                "当前版本未连接真实大模型服务，您可以：\n"
                "1. 尝试使用更具体的检测指令，如「检测图片 xxx.jpg」\n"
                "2. 询问火灾烟雾检测相关知识，如「火焰检测的原理是什么」\n"
                "3. 查询检测统计，如「查看检测统计」\n"
                "4. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
            )
        history_hint = "，并已读取最近的会话上下文" if history else ""
        return (
            f"这是本地占位回复：已收到你的消息「{normalized[:50]}」{history_hint}。\n"
            "当前版本未连接真实大模型服务。您可以：\n"
            "1. 尝试使用检测相关指令，如「检测图片」「视频检测」「知识检索」等\n"
            "2. 查看检测统计：输入「统计概览」或「历史记录」\n"
            "3. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
        )

    # ══════════════════════════════════════════════════════════════
    # SSE 流式接口
    # ══════════════════════════════════════════════════════════════

    async def send_message_stream(self, user_id: int, data, session_id: int = None):
        """
        SSE 流式发送消息（异步生成器），集成 Agent 流程。

        内部自行创建和管理 DB Session，避免 FastAPI Depends 提前关闭连接。

        Yields SSE 事件:
        - event: start, data: {session_id, message_id}
        - event: token, data: {content: "xxx"}
        - event: tool_call, data: {tool: "xxx", args: {...}}
        - event: done, data: {tokens_used, latency_ms, message_id, tool_calls, tool_result}
        - event: error, data: {content: "xxx"}
        """
        from app.database.session import SessionLocal

        db = SessionLocal()
        user_msg_id = None
        try:
            # 获取或创建会话
            if session_id:
                session = self._get_user_session(db, session_id, user_id)
            else:
                session = self.create_session(db, user_id)

            # 构建消息内容（如果包含文件，注入文件信息提示）
            agent_content = data.content
            if data.files:
                file_hints = []
                for f in data.files:
                    file_type = f.get("type", "file")
                    file_url = f.get("url", "")
                    file_name = f.get("name", "")
                    if file_type == "image":
                        file_hints.append(f"用户上传了图片: {file_url}，请检测这张图片")
                    elif file_type == "zip":
                        file_hints.append(f"用户上传了ZIP压缩包: {file_url}，请检测压缩包中的图片")
                    elif file_type == "video":
                        file_hints.append(f"用户上传了视频: {file_url}，请检测该视频")
                    else:
                        file_hints.append(f"用户上传了文件: {file_url}（{file_name}）")
                agent_content = "\n".join(file_hints) + "\n" + data.content

            # 存储用户消息
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=agent_content,
                agent_used="user",
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
            user_msg_id = user_msg.id

            # 加载历史上下文
            history_messages = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session.id,
                    ChatMessage.id != user_msg.id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

            # 发送 thinking 事件（保留 start 向后兼容）
            start_data = {'session_id': session.id, 'message_id': user_msg.id}
            yield f"event: thinking\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"
            yield f"event: start\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"

            start_time = time.time()

            if settings.LLM_STUB_MODE:
                # ── Stub 模式：模拟 Agent 流式输出 ──
                # 先发送"思考中"的提示（text_chunk 新事件名，保留 token 向后兼容）
                thinking_content = '🔍 正在分析您的问题...'
                yield f"event: text_chunk\ndata: {json.dumps({'content': thinking_content}, ensure_ascii=False)}\n\n"
                yield f"event: token\ndata: {json.dumps({'content': thinking_content}, ensure_ascii=False)}\n\n"

                # 意图识别
                normalized = agent_content.strip()
                tool_calls = []
                tool_result = ""

                # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
                files = data.files
                image_detected = False
                if files and self._has_image_file(files):
                    has_detect_keyword = any(
                        kw in normalized for kw in ["检测", "识别", "看看", "分析"]
                    )
                    if has_detect_keyword or not data.content.strip():
                        # 提取第一个图片 URL，直接调用单图检测
                        image_url = self._extract_first_image_url(files)
                        if image_url:
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": image_url}
                            tool_calls = [{"tool": tool_name, "args": tool_args}]

                            logger.info(
                                "SSE Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                                image_url,
                            )

                            # 发送工具开始事件
                            tool_start_data = {'tool': tool_name, 'input': tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                tool_result = self._invoke_tool_stub(tool_name, tool_args)
                                json.loads(tool_result)  # 校验返回是否为有效 JSON
                            except json.JSONDecodeError:
                                logger.warning("SSE Stub 图片检测工具返回非 JSON 结果: %s", tool_result)
                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                            except Exception as e:
                                logger.exception("SSE Stub 图片检测工具调用失败: %s", e)
                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                            # 发送工具结束事件（含完整结果，供前端解析标注图）
                            tool_end_data = {'tool': tool_name, 'result': tool_result}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                            # 发送专用工具结果事件，前端可据此渲染 DetectionResultCard
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                            # 发送文字摘要到聊天正文
                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
                            result_content = "\n\n" + display_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            full_content = self._format_agent_response(
                                user_message=normalized,
                                tool_name=tool_name,
                                tool_description="单图火焰烟雾检测",
                                tool_result=tool_result,
                            )
                            image_detected = True

                if not image_detected:
                    matched_tool = self._match_intent(normalized)

                    if matched_tool:
                        tool_name = matched_tool["name"]
                        tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
                        tool_calls = [{"tool": tool_name, "args": tool_args}]

                        # 发送工具开始事件（tool_start 新事件名，保留 tool_call 向后兼容）
                        tool_start_data = {'tool': tool_name, 'input': tool_args}
                        yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                        yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                        try:
                            tool_result = self._invoke_tool_stub(tool_name, tool_args)
                        except Exception as e:
                            logger.exception("SSE Stub 工具调用失败: tool=%s", tool_name)
                            tool_result = json.dumps({"error": f"工具调用失败：{str(e)}"}, ensure_ascii=False)

                        # 发送工具结束事件（tool_end 新事件名）
                        tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                        yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                        # 发送工具结果事件（text_chunk 新事件名，保留 token 向后兼容）
                        display_text = self._extract_tool_result_summary(tool_name, tool_result)
                        result_content = "\n\n" + display_text
                        yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                        yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                        full_content = self._format_agent_response(
                            user_message=normalized,
                            tool_name=tool_name,
                            tool_description=matched_tool["description"],
                            tool_result=tool_result,
                        )
                    else:
                        full_content = self._build_stub_reply(normalized, history)
                        # 流式输出回复内容（text_chunk 新事件名，保留 token 向后兼容）
                        for offset in range(0, len(full_content), 8):
                            chunk = full_content[offset : offset + 8]
                            yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                # ── 真实模式：复用 DetectionAgent 单例流式输出 ──
                try:
                    if not detection_agent.available:
                        raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

                    full_content = ""
                    tool_calls = []
                    tool_result = ""

                    # 若用户上传了图片，先直接调用检测工具，避免把 base64 标注图
                    # 送入 LLM 上下文导致 token 超限；只把文字摘要交给 Agent。
                    if data.files and self._has_image_file(data.files):
                        first_image_url = self._extract_first_image_url(data.files)
                        if first_image_url:
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": first_image_url, "conf": 0.25, "iou": 0.45}
                            tool_calls.append({"tool": tool_name, "args": tool_args})

                            tool_start_data = {"tool": tool_name, "input": tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                from app.agent.tools.detection_tool import detect_single_image
                                loop = asyncio.get_event_loop()
                                tool_result = await loop.run_in_executor(
                                    None,
                                    lambda: detect_single_image.invoke(tool_args),
                                )
                                json.loads(tool_result)  # 校验返回是否为有效 JSON
                            except json.JSONDecodeError:
                                logger.warning("真实模式图片检测工具返回非 JSON 结果: %s", tool_result)
                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                            except Exception as e:
                                logger.exception("真实模式图片预处理检测失败")
                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)

                            # 发送完整工具结果，前端可解析标注图
                            tool_end_data = {"tool": tool_name, "result": tool_result}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"

                            # 在聊天正文显示文字摘要
                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
                            result_content = "\n\n" + display_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            # 只把摘要注入 Agent 提示词，避免 base64 撑爆上下文
                            agent_content = (
                                f"{agent_content}\n\n【系统提示】已对用户上传的图片完成火灾烟雾检测，"
                                f"检测结果摘要如下（请不要再次调用检测工具）：\n{display_text}\n"
                                f"请直接基于以上结果回复用户。"
                            )

                    async for event in detection_agent.chat_stream(agent_content, history):
                        event_type = event.get("type", "")

                        if event_type == "text_chunk":
                            token_text = event.get("content", "")
                            full_content += token_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"

                        elif event_type == "tool_call":
                            tool_name = event.get("tool", "")
                            tool_input = event.get("input", {})
                            tool_calls.append({"tool": tool_name, "args": tool_input})
                            tool_start_data = {'tool': tool_name, 'input': tool_input}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                        elif event_type == "tool_result":
                            tool_output = event.get("result", "")
                            tool_name = event.get("tool", "")
                            if tool_output:
                                tool_result += str(tool_output) + "\n"
                                # 发送完整工具结果，前端可解析标注图
                                tool_end_data = {'tool': tool_name, 'result': tool_output}
                                yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
                                yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_output}, ensure_ascii=False)}\n\n"

                        elif event_type == "error":
                            error_content = event.get("content", "") or event.get("message", "")
                            if not error_content:
                                error_content = "AI 服务暂时不可用，请稍后重试。"
                            yield f"event: error\ndata: {json.dumps({'content': error_content}, ensure_ascii=False)}\n\n"

                    if not full_content:
                        full_content = "抱歉，无法处理您的请求。"

                except Exception as e:
                    logger.exception("SSE Agent 执行失败")
                    full_content = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
                    tool_calls = []
                    tool_result = ""
                    yield f"event: error\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(data.content) + len(full_content)) // 2)

            # 存储 AI 回复到数据库
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                agent_used="react_agent",
                tool_calls=tool_calls if tool_calls else None,
                tool_result=tool_result if tool_result else None,
                tokens_used=tokens_used if tokens_used > 0 else None,
                latency_ms=latency_ms if latency_ms > 0 else None,
            )
            db.add(assistant_msg)

            # 更新会话
            session.message_count = (session.message_count or 0) + 2
            session.last_message_at = datetime.now(timezone.utc)
            if session.message_count == 2:
                session.title = data.content[:50] if len(data.content) > 50 else data.content
            db.commit()
            db.refresh(assistant_msg)

            # 发送 done 事件，包含 session_id 以便前端自动关联新会话
            done_data = {
                "session_id": session.id,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "message_id": assistant_msg.id,
                "tool_calls": tool_calls if tool_calls else [],
                "tool_result": tool_result if tool_result else "",
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            db.rollback()
            logger.error("SSE流式输出错误: %s", e)
            yield f"event: error\ndata: {json.dumps({'content': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
        finally:
            db.close()


# 全局单例
chat_service = ChatService()
```
**当前版本（缺失/被改）**：
```python
"""
对话服务
处理 Agent/Chat 会话和消息的 CRUD 业务逻辑

集成 ReAct Agent：
- LLM_STUB_MODE=true 时：使用占位逻辑，模拟 Agent 思考→工具调用→回复的流程
- LLM_STUB_MODE=false 时：使用真实的 LangChain ChatOpenAI + ReAct Agent
"""

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agent.detection_agent import detection_agent
from app.entity.db_models import ChatSession, ChatMessage
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """对话服务，集成 ReAct Agent 实现智能火灾烟雾检测对话"""

    # ── 工具名称到意图关键词的映射（用于 Stub 模式下的意图识别） ──
    _TOOL_INTENT_MAP = {
        "detect_single_image": {
            "keywords": ["检测", "识别", "图片", "图像", "照片", "单张", "单图", "这张"],
            "description": "单图火焰烟雾检测",
        },
        "detect_batch_images": {
            "keywords": ["批量", "多张", "多图", "一组", "这些图片", "批量检测"],
            "description": "批量图片检测",
        },
        "detect_zip_images_file": {
            "keywords": ["zip", "压缩包", "打包", "压缩文件", "解压"],
            "description": "ZIP 压缩包检测",
        },
        "detect_video_file": {
            "keywords": ["视频", "录像", "监控", "mp4", "avi", "摄像头"],
            "description": "视频检测",
        },
        "search_knowledge": {
            "keywords": ["知识", "原理", "怎么", "如何", "为什么", "什么", "介绍", "说明", "解释", "特点", "应用"],
            "description": "知识检索",
        },
        "query_detection_stats": {
            "keywords": ["统计", "概览", "总览", "数据", "统计数", "统计概览", "整体情况"],
            "description": "统计查询",
        },
        "query_detection_history": {
            "keywords": ["历史", "记录", "历史记录", "检测记录", "最近", "之前"],
            "description": "历史查询",
        },
        "query_user_list": {
            "keywords": ["用户", "人员", "账号", "成员", "用户列表", "谁"],
            "description": "用户查询",
        },
    }

    # ══════════════════════════════════════════════════════════════
    # 会话管理方法（保持不变）
    # ══════════════════════════════════════════════════════════════

    def create_session(self, db: Session, user_id: int, title: Optional[str] = None) -> ChatSession:
        """
        创建对话会话
        Args:
            db: 数据库会话
            user_id: 用户 ID
            title: 会话标题（可选，默认"新对话"）
        Returns:
            新创建的会话对象
        """
        session_uuid = str(uuid.uuid4())
        chat_session = ChatSession(
            user_id=user_id,
            session_uuid=session_uuid,
            title=title or "新对话",
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        logger.info(f"创建会话成功: user_id={user_id}, uuid={session_uuid}")
        return chat_session

    def get_sessions(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """获取用户会话列表（分页）"""
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
        total = query.count()
        sessions = (
            query.order_by(desc(ChatSession.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "id": s.id,
                    "session_uuid": s.session_uuid,
                    "title": s.title,
                    "status": s.status,
                    "message_count": s.message_count,
                    "last_message_at": s.last_message_at,
                    "created_at": s.created_at,
                }
                for s in sessions
            ],
        }

    def get_session_messages(
        self,
        db: Session,
        session_id: int,
        user_id: int,
    ) -> list[dict]:
        """获取会话消息历史"""
        self._get_user_session(db, session_id, user_id)
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "agent_used": m.agent_used,
                "tool_calls": m.tool_calls,
                "tool_result": m.tool_result,
                "tokens_used": m.tokens_used,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    def send_message(
        self,
        db: Session,
        session_id: int,
        user_id: int,
        content: str,
        files: list = None,
    ) -> dict:
        """
        发送消息并存储（集成 ReAct Agent 流程）
        Args:
            db: 数据库会话
            session_id: 会话 ID
            user_id: 用户 ID
            content: 消息内容
            files: 上传的文件列表（可选）
        Returns:
            包含 user_message 和 assistant_message 的字典
        """
        session = self._get_user_session(db, session_id, user_id)

        # 构建存储到数据库的消息内容（包含图片 URL 信息，用于多轮对话记忆）
        stored_content = content
        if files:
            file_hints = []
            for f in files:
                file_type = f.get("type", "file")
                file_url = f.get("url", "")
                file_name = f.get("name", "")
                if file_type == "image":
                    file_hints.append(f"[用户上传了图片: {file_url}]")
                elif file_type == "zip":
                    file_hints.append(f"[用户上传了ZIP压缩包: {file_url}]")
                elif file_type == "video":
                    file_hints.append(f"[用户上传了视频: {file_url}]")
                else:
                    file_hints.append(f"[用户上传了文件: {file_url} ({file_name})]")
            if file_hints:
                stored_content = "\n".join(file_hints) + "\n" + content

        # 存储用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=stored_content,
        )
        db.add(user_msg)
        db.flush()

        # 加载会话历史作为 LLM 上下文
        history_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

        # AI 回复（通过 Agent 流程生成）
        reply_content, tool_calls, tool_result, tokens_used, latency_ms = self._run_agent(
            content, history=history, files=files
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=reply_content,
            agent_used="react_agent",
            tool_calls=tool_calls if tool_calls else None,
            tool_result=tool_result if tool_result else None,
            tokens_used=tokens_used if tokens_used > 0 else None,
            latency_ms=latency_ms if latency_ms > 0 else None,
        )
        db.add(assistant_msg)

        # 更新会话信息
        session.message_count = (session.message_count or 0) + 2
        session.last_message_at = datetime.now(timezone.utc)
        if session.message_count == 2:
            session.title = content[:50] if len(content) > 50 else content

        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        return {
            "user_message": {
                "id": user_msg.id,
                "session_id": user_msg.session_id,
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at,
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "session_id": assistant_msg.session_id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "agent_used": assistant_msg.agent_used,
                "tool_calls": assistant_msg.tool_calls,
                "tool_result": assistant_msg.tool_result,
                "created_at": assistant_msg.created_at,
            },
        }

    def delete_session(self, db: Session, session_id: int, user_id: int) -> bool:
        """删除会话（含消息级联删除）"""
        session = self._get_user_session(db, session_id, user_id)
        db.delete(session)
        db.commit()
        logger.info(f"删除会话成功: session_id={session_id}, user_id={user_id}")
        return True

    def _get_user_session(self, db: Session, session_id: int, user_id: int) -> ChatSession:
        """获取用户所属会话（验证权限）"""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        return session

    # ══════════════════════════════════════════════════════════════
    # Agent 核心逻辑
    # ══════════════════════════════════════════════════════════════

    def _run_agent(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        运行 Agent 流程，生成回复。

        根据 LLM_STUB_MODE 配置选择不同的执行路径：
        - True：使用占位模拟流程（不依赖外部 LLM API）
        - False：使用真实的 LangChain ReAct Agent

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表

        Returns:
            tuple: (回复内容, tool_calls列表, tool_result字符串, token数, 延迟毫秒数)
        """
        if settings.LLM_STUB_MODE:
            return self._run_agent_stub(content, history, files)
        else:
            return self._run_agent_real(content, history)

    def _run_agent_stub(self, content: str, history: list = None, files: list = None) -> tuple:
        """
        Stub 模式：模拟 ReAct Agent 的思考→工具调用→回复流程。

        流程：
        1. 意图识别：根据关键词匹配确定用户意图
        2. 工具调用：模拟 Agent 选择合适的工具并执行
        3. 结果汇总：将工具返回结果格式化为自然语言回复

        Args:
            content: 用户消息内容
            history: 历史消息列表
            files: 上传的文件列表，每个文件包含 url/type/name 字段
        """
        start_time = time.time()
        tool_calls = []
        tool_result = ""

        normalized = content.strip()

        # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
        if files and self._has_image_file(files):
            has_detect_keyword = any(
                kw in normalized for kw in ["检测", "识别", "看看", "分析"]
            )
            if has_detect_keyword or not normalized:
                # 提取第一个图片 URL
                image_url = self._extract_first_image_url(files)
                if image_url:
                    tool_name = "detect_single_image"
                    tool_args = {"image_path": image_url}
                    tool_calls = [{"tool": tool_name, "args": tool_args}]

                    logger.info(
                        "Agent Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                        image_url,
                    )

                    try:
                        tool_result = self._invoke_tool_stub(tool_name, tool_args)
                    except Exception as e:
                        logger.exception("Agent Stub 图片检测工具调用失败: %s", e)
                        tool_result = f"工具调用失败：{str(e)}"

                    reply = self._format_agent_response(
                        user_message=normalized,
                        tool_name=tool_name,
                        tool_description="单图火焰烟雾检测",
                        tool_result=tool_result,
                    )

                    latency_ms = int((time.time() - start_time) * 1000)
                    tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)
                    return reply, tool_calls, tool_result, tokens_used, latency_ms

        # ── 步骤 1：意图识别 ──
        # 根据关键词匹配，找到最可能的工具意图
        matched_tool = self._match_intent(normalized)

        # ── 步骤 2：工具调用（模拟） ──
        if matched_tool:
            tool_name = matched_tool["name"]
            tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
            tool_calls = [{"tool": tool_name, "args": tool_args}]

            logger.info(
                "Agent Stub: 意图=%s, 工具=%s, 参数=%s",
                matched_tool["description"], tool_name, tool_args,
            )

            try:
                tool_result = self._invoke_tool_stub(tool_name, tool_args)
            except Exception as e:
                logger.exception("Agent Stub 工具调用失败: tool=%s", tool_name)
                tool_result = f"工具调用失败：{str(e)}"

            # ── 步骤 3：生成自然语言回复 ──
            reply = self._format_agent_response(
                user_message=normalized,
                tool_name=tool_name,
                tool_description=matched_tool["description"],
                tool_result=tool_result,
            )
        else:
            # 无法匹配到具体工具，使用通用回复
            reply = self._build_stub_reply(normalized, history)

        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = max(1, (len(content) + len(reply) + len(tool_result)) // 2)

        return reply, tool_calls, tool_result, tokens_used, latency_ms

    def _run_agent_real(self, content: str, history: list = None) -> tuple:
        """
        真实模式：复用 DetectionAgent 单例执行对话。

        DetectionAgent 已在 detection_agent.py 中根据 settings 完成 LLM 配置，
        这里直接调用其 chat() 方法，避免重复创建 LLM 和 AgentExecutor 实例。
        """
        start_time = time.time()

        try:
            if not detection_agent.available:
                raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

            # 调用 detection_agent.chat()（异步 → 同步）
            result = asyncio.run(detection_agent.chat(content, history))

            reply_content = result.get("output", "抱歉，无法处理您的请求。")

            # 提取工具调用信息
            tool_calls = []
            tool_result_str = ""
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                action, observation = step
                tool_calls.append({
                    "tool": action.tool,
                    "args": action.tool_input,
                })
                if isinstance(observation, str):
                    tool_result_str += observation + "\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(content) + len(reply_content) + len(tool_result_str)) // 2)

            return reply_content, tool_calls, tool_result_str.strip(), tokens_used, latency_ms

        except Exception as e:
            logger.exception("ReAct Agent 执行失败")
            reply = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
            latency_ms = int((time.time() - start_time) * 1000)
            return reply, [], "", 0, latency_ms

    # ══════════════════════════════════════════════════════════════
    # Stub 模式辅助方法
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _has_image_file(files: list) -> bool:
        """检查文件列表中是否包含图片类型文件"""
        if not files:
            return False
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                return True
        return False

    @staticmethod
    def _extract_first_image_url(files: list) -> Optional[str]:
        """从文件列表中提取第一个图片文件的 URL"""
        if not files:
            return None
        for f in files:
            if not isinstance(f, dict):
                continue
            # 正常情况：前端应发 { url, type, name }
            file_type = f.get("type")
            if not file_type:
                # 防御性兼容：前端忘记解包 res.data，发送了 { code, data: { url, type, name } }
                file_type = f.get("data", {}).get("type")
            if file_type == "image":
                url = f.get("url") or f.get("data", {}).get("url", "")
                if url:
                    return url
        return None

    def _match_intent(self, content: str) -> Optional[dict]:
        """
        根据用户消息内容匹配最可能的工具意图。

        使用关键词匹配 + 得分排序，找到最匹配的工具。

        Args:
            content: 用户消息内容

        Returns:
            dict 或 None: 匹配到的工具信息 {"name": ..., "description": ...}
        """
        content_lower = content.lower()
        best_score = 0
        best_tool = None

        for tool_name, info in self._TOOL_INTENT_MAP.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword.lower() in content_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_tool = {"name": tool_name, "description": info["description"]}

        return best_tool if best_score > 0 else None

    def _extract_tool_args_from_stub(self, content: str, tool_name: str) -> dict:
        """
        从用户消息中提取工具调用参数（Stub 模式下的简单参数提取）。

        使用正则表达式提取常见参数模式。

        Args:
            content: 用户消息内容
            tool_name: 匹配到的工具名称

        Returns:
            dict: 工具参数字典
        """
        args = {}

        # 提取置信度参数（如 "置信度 0.5"、"conf=0.3"）
        conf_match = re.search(r'(?:置信度|conf(?:idence)?)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if conf_match:
            args["conf"] = float(conf_match.group(1))

        # 提取帧率参数（如 "每5帧"、"采样率10"、"帧率3"）
        frame_match = re.search(r'(?:每\s*(\d+)\s*帧|采样率[=：:\s]*(\d+)|帧率[=：:\s]*(\d+))', content)
        if frame_match:
            frame_val = next(v for v in frame_match.groups() if v is not None)
            args["frame_sample_rate"] = int(frame_val)

        # 提取 IoU 参数
        iou_match = re.search(r'(?:iou|nms)[=：:\s]*([\d.]+)', content, re.IGNORECASE)
        if iou_match:
            args["iou"] = float(iou_match.group(1))

        # 提取文件路径（简单模式：匹配常见的文件路径格式）
        path_match = re.search(r'(?:路径|文件|图片|视频|zip)[=：:\s]*([^\s,，。]+\.(?:jpg|jpeg|png|bmp|mp4|avi|zip))', content, re.IGNORECASE)
        if path_match:
            path_val = path_match.group(1)
            if tool_name in ("detect_single_image",):
                args["image_path"] = path_val
            elif tool_name == "detect_video_file":
                args["video_path"] = path_val
            elif tool_name == "detect_zip_images_file":
                args["zip_path"] = path_val

        # 提取页码
        page_match = re.search(r'(?:第\s*(\d+)\s*页|page[=：:\s]*(\d+))', content, re.IGNORECASE)
        if page_match:
            page_val = next(v for v in page_match.groups() if v is not None)
            args["page"] = int(page_val)

        return args

    def _invoke_tool_stub(self, tool_name: str, args: dict) -> str:
        """
        在 Stub 模式下调用工具（直接调用工具函数，不经过 LLM）。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            str: 工具返回结果
        """
        from app.agent.tools.detection_tool import (
            detect_single_image,
            detect_batch_images,
            detect_zip_images_file,
            detect_video_file,
        )
        from app.agent.tools.knowledge_tool import search_knowledge
        from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
        from app.agent.tools.user_tool import query_user_list

        tool_map = {
            "detect_single_image": detect_single_image,
            "detect_batch_images": detect_batch_images,
            "detect_zip_images_file": detect_zip_images_file,
            "detect_video_file": detect_video_file,
            "search_knowledge": search_knowledge,
            "query_detection_stats": query_detection_stats,
            "query_detection_history": query_detection_history,
            "query_user_list": query_user_list,
        }

        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return f"未知工具：{tool_name}"

        # 调用工具（LangChain @tool 装饰的函数可以直接调用）
        return tool_func.invoke(args)

    def _format_agent_response(
        self,
        user_message: str,
        tool_name: str,
        tool_description: str,
        tool_result: str,
    ) -> str:
        """
        将工具调用结果格式化为自然语言回复。

        模拟 Agent 在获得工具结果后，生成用户友好的回复。

        Args:
            user_message: 用户原始消息
            tool_name: 使用的工具名称
            tool_description: 工具描述
            tool_result: 工具返回的结果

        Returns:
            str: 格式化的自然语言回复
        """
        # 根据工具类型生成不同的回复前缀
        prefixes = {
            "detect_single_image": "已为您完成单图火焰烟雾检测，以下是检测结果：",
            "detect_batch_images": "已为您完成批量图片火焰烟雾检测，以下是检测结果：",
            "detect_zip_images_file": "已为您完成 ZIP 压缩包中图片的火焰烟雾检测，以下是检测结果：",
            "detect_video_file": "已为您完成视频火焰烟雾检测，以下是检测结果：",
            "search_knowledge": "已为您检索火灾烟雾检测相关知识，以下是检索结果：",
            "query_detection_stats": "已为您查询检测统计概览，以下是统计数据：",
            "query_detection_history": "已为您查询检测历史记录，以下是历史记录：",
            "query_user_list": "已为您查询系统用户列表，以下是用户信息：",
        }

        prefix = prefixes.get(tool_name, f"已为您执行{tool_description}，以下是结果：")

        return f"{prefix}\n\n{tool_result}"

    @staticmethod
    def _build_stub_reply(content: str, history: list = None) -> str:
        """
        根据输入生成确定性的本地占位回复，不访问任何外部大模型服务。

        当无法匹配到具体工具意图时，使用此方法生成通用回复。
        """
        normalized = content.strip()
        if any(keyword in normalized for keyword in ("火", "烟", "告警", "检测")):
            return (
                "这是本地占位回复：已收到火灾烟雾检测相关问题。\n"
                "当前版本未连接真实大模型服务，您可以：\n"
                "1. 尝试使用更具体的检测指令，如「检测图片 xxx.jpg」\n"
                "2. 询问火灾烟雾检测相关知识，如「火焰检测的原理是什么」\n"
                "3. 查询检测统计，如「查看检测统计」\n"
                "4. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
            )
        history_hint = "，并已读取最近的会话上下文" if history else ""
        return (
            f"这是本地占位回复：已收到你的消息「{normalized[:50]}」{history_hint}。\n"
            "当前版本未连接真实大模型服务。您可以：\n"
            "1. 尝试使用检测相关指令，如「检测图片」「视频检测」「知识检索」等\n"
            "2. 查看检测统计：输入「统计概览」或「历史记录」\n"
            "3. 配置 LLM API 密钥后，即可使用完整的 AI Agent 对话功能。"
        )

    # ══════════════════════════════════════════════════════════════
    # SSE 流式接口
    # ══════════════════════════════════════════════════════════════

    async def send_message_stream(self, user_id: int, data, session_id: int = None):
        """
        SSE 流式发送消息（异步生成器），集成 Agent 流程。

        内部自行创建和管理 DB Session，避免 FastAPI Depends 提前关闭连接。

        Yields SSE 事件:
        - event: start, data: {session_id, message_id}
        - event: token, data: {content: "xxx"}
        - event: tool_call, data: {tool: "xxx", args: {...}}
        - event: done, data: {tokens_used, latency_ms, message_id, tool_calls, tool_result}
        - event: error, data: {message: "xxx"}
        """
        from app.database.session import SessionLocal

        db = SessionLocal()
        user_msg_id = None
        try:
            # 获取或创建会话
            if session_id:
                session = self._get_user_session(db, session_id, user_id)
            else:
                session = self.create_session(db, user_id)

            # 构建消息内容（如果包含文件，注入文件信息提示）
            agent_content = data.content
            if data.files:
                file_hints = []
                for f in data.files:
                    file_type = f.get("type", "file")
                    file_url = f.get("url", "")
                    file_name = f.get("name", "")
                    if file_type == "image":
                        file_hints.append(f"用户上传了图片: {file_url}，请检测这张图片")
                    elif file_type == "zip":
                        file_hints.append(f"用户上传了ZIP压缩包: {file_url}，请检测压缩包中的图片")
                    elif file_type == "video":
                        file_hints.append(f"用户上传了视频: {file_url}，请检测该视频")
                    else:
                        file_hints.append(f"用户上传了文件: {file_url}（{file_name}）")
                agent_content = "\n".join(file_hints) + "\n" + data.content

            # 存储用户消息
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=agent_content,
                agent_used="user",
            )
            db.add(user_msg)
            db.commit()
            db.refresh(user_msg)
            user_msg_id = user_msg.id

            # 加载历史上下文
            history_messages = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session.id,
                    ChatMessage.id != user_msg.id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in reversed(history_messages)]

            # 发送 thinking 事件（保留 start 向后兼容）
            start_data = {'session_id': session.id, 'message_id': user_msg.id}
            yield f"event: thinking\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"
            yield f"event: start\ndata: {json.dumps(start_data, ensure_ascii=False)}\n\n"

            start_time = time.time()

            if settings.LLM_STUB_MODE:
                # ── Stub 模式：模拟 Agent 流式输出 ──
                # 先发送"思考中"的提示（text_chunk 新事件名，保留 token 向后兼容）
                thinking_content = '🔍 正在分析您的问题...'
                yield f"event: text_chunk\ndata: {json.dumps({'content': thinking_content}, ensure_ascii=False)}\n\n"
                yield f"event: token\ndata: {json.dumps({'content': thinking_content}, ensure_ascii=False)}\n\n"

                # 意图识别
                normalized = agent_content.strip()
                tool_calls = []
                tool_result = ""

                # ── 优先处理：如果用户上传了图片且消息包含"检测"关键词，直接调用单图检测 ──
                files = data.files
                image_detected = False
                if files and self._has_image_file(files):
                    has_detect_keyword = any(
                        kw in normalized for kw in ["检测", "识别", "看看", "分析"]
                    )
                    if has_detect_keyword or not data.content.strip():
                        # 提取第一个图片 URL，直接调用单图检测
                        image_url = self._extract_first_image_url(files)
                        if image_url:
                            tool_name = "detect_single_image"
                            tool_args = {"image_path": image_url}
                            tool_calls = [{"tool": tool_name, "args": tool_args}]

                            logger.info(
                                "SSE Stub: 检测到上传图片，直接调用单图检测, URL=%s",
                                image_url,
                            )

                            # 发送工具开始事件
                            tool_start_data = {'tool': tool_name, 'args': tool_args}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                            try:
                                tool_result = self._invoke_tool_stub(tool_name, tool_args)
                            except Exception as e:
                                logger.exception("SSE Stub 图片检测工具调用失败: %s", e)
                                tool_result = f"工具调用失败：{str(e)}"

                            # 发送工具结束事件
                            tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                            # 发送工具结果事件
                            nl = "\n\n"
                            result_content = nl + tool_result
                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                            full_content = self._format_agent_response(
                                user_message=normalized,
                                tool_name=tool_name,
                                tool_description="单图火焰烟雾检测",
                                tool_result=tool_result,
                            )
                            image_detected = True

                if not image_detected:
                    matched_tool = self._match_intent(normalized)

                    if matched_tool:
                        tool_name = matched_tool["name"]
                        tool_args = self._extract_tool_args_from_stub(normalized, tool_name)
                        tool_calls = [{"tool": tool_name, "args": tool_args}]

                        # 发送工具开始事件（tool_start 新事件名，保留 tool_call 向后兼容）
                        tool_start_data = {'tool': tool_name, 'args': tool_args}
                        yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                        yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                        try:
                            tool_result = self._invoke_tool_stub(tool_name, tool_args)
                        except Exception as e:
                            logger.exception("SSE Stub 工具调用失败: tool=%s", tool_name)
                            tool_result = f"工具调用失败：{str(e)}"

                        # 发送工具结束事件（tool_end 新事件名）
                        tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                        yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                        # 发送工具结果事件（text_chunk 新事件名，保留 token 向后兼容）
                        nl = "\n\n"
                        result_content = nl + tool_result
                        yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                        yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"

                        full_content = self._format_agent_response(
                            user_message=normalized,
                            tool_name=tool_name,
                            tool_description=matched_tool["description"],
                            tool_result=tool_result,
                        )
                    else:
                        full_content = self._build_stub_reply(normalized, history)
                        # 流式输出回复内容（text_chunk 新事件名，保留 token 向后兼容）
                        for offset in range(0, len(full_content), 8):
                            chunk = full_content[offset : offset + 8]
                            yield f"event: text_chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                # ── 真实模式：复用 DetectionAgent 单例流式输出 ──
                try:
                    if not detection_agent.available:
                        raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")

                    full_content = ""
                    tool_calls = []
                    tool_result = ""

                    async for event in detection_agent.chat_stream(agent_content, history):
                        event_type = event.get("type", "")

                        if event_type == "text_chunk":
                            token_text = event.get("content", "")
                            full_content += token_text
                            yield f"event: text_chunk\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"
                            yield f"event: token\ndata: {json.dumps({'content': token_text}, ensure_ascii=False)}\n\n"

                        elif event_type == "tool_call":
                            tool_name = event.get("tool", "")
                            tool_input = event.get("input", {})
                            tool_calls.append({"tool": tool_name, "args": tool_input})
                            tool_start_data = {'tool': tool_name, 'args': tool_input}
                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"

                        elif event_type == "tool_result":
                            tool_output = event.get("result", "")
                            tool_name = event.get("tool", "")
                            if tool_output:
                                tool_result += str(tool_output) + "\n"
                                tool_end_data = {'tool': tool_name, 'result': str(tool_output)[:500]}
                                yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"

                        elif event_type == "error":
                            error_content = event.get("content", "")
                            yield f"event: error\ndata: {json.dumps({'message': error_content}, ensure_ascii=False)}\n\n"

                    if not full_content:
                        full_content = "抱歉，无法处理您的请求。"

                except Exception as e:
                    logger.exception("SSE Agent 执行失败")
                    full_content = f"AI 服务暂时不可用，请稍后重试。"
                    tool_calls = []
                    tool_result = ""
                    yield f"event: text_chunk\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"
                    yield f"event: token\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = max(1, (len(data.content) + len(full_content)) // 2)

            # 存储 AI 回复到数据库
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                agent_used="react_agent",
                tool_calls=tool_calls if tool_calls else None,
                tool_result=tool_result if tool_result else None,
                tokens_used=tokens_used if tokens_used > 0 else None,
                latency_ms=latency_ms if latency_ms > 0 else None,
            )
            db.add(assistant_msg)

            # 更新会话
            session.message_count = (session.message_count or 0) + 2
            session.last_message_at = datetime.now(timezone.utc)
            if session.message_count == 2:
                session.title = data.content[:50] if len(data.content) > 50 else data.content
            db.commit()
            db.refresh(assistant_msg)

            # 发送 done 事件，包含 session_id 以便前端自动关联新会话
            done_data = {
                "session_id": session.id,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "message_id": assistant_msg.id,
                "tool_calls": tool_calls if tool_calls else [],
                "tool_result": tool_result if tool_result else "",
            }
            yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            db.rollback()
            logger.error("SSE流式输出错误: %s", e)
            yield f"event: error\ndata: {json.dumps({'message': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
        finally:
            db.close()


# 全局单例
chat_service = ChatService()
```
**统一差异（unified diff）**：
```diff
--- backup/backend/app/services/chat_service.py
+++ current/backend/app/services/chat_service.py
@@ -8,7 +8,6 @@
 """
 
 import asyncio
-import concurrent.futures
 import json
 import re
 import time
@@ -304,7 +303,7 @@
         if settings.LLM_STUB_MODE:
             return self._run_agent_stub(content, history, files)
         else:
-            return self._run_agent_real(content, history, files)
+            return self._run_agent_real(content, history)
 
     def _run_agent_stub(self, content: str, history: list = None, files: list = None) -> tuple:
         """
@@ -398,66 +397,36 @@
 
         return reply, tool_calls, tool_result, tokens_used, latency_ms
 
-    def _run_agent_real(self, content: str, history: list = None, files: list = None) -> tuple:
+    def _run_agent_real(self, content: str, history: list = None) -> tuple:
         """
         真实模式：复用 DetectionAgent 单例执行对话。
 
         DetectionAgent 已在 detection_agent.py 中根据 settings 完成 LLM 配置，
         这里直接调用其 chat() 方法，避免重复创建 LLM 和 AgentExecutor 实例。
-
-        如果用户上传了图片，会先在函数内调用检测工具获取完整结果，再把文字摘要
-        注入提示词交给 Agent，避免把 base64 标注图送入 LLM 上下文导致 token 超限。
         """
         start_time = time.time()
-        tool_calls = []
-        tool_result_str = ""
 
         try:
             if not detection_agent.available:
                 raise RuntimeError("DetectionAgent 不可用，请检查 LLM 配置")
 
-            # 若用户上传图片，先直接检测并把摘要注入提示词
-            if files and self._has_image_file(files):
-                first_image_url = self._extract_first_image_url(files)
-                if first_image_url:
-                    tool_name = "detect_single_image"
-                    tool_args = {"image_path": first_image_url, "conf": 0.25, "iou": 0.45}
-                    tool_calls.append({"tool": tool_name, "args": tool_args})
-
-                    try:
-                        from app.agent.tools.detection_tool import detect_single_image
-                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
-                            tool_result_str = executor.submit(
-                                detect_single_image.invoke, tool_args
-                            ).result()
-                    except Exception as e:
-                        logger.exception("真实模式图片预处理检测失败")
-                        tool_result_str = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)
-
-                    display_text = self._extract_tool_result_summary(tool_name, tool_result_str)
-                    content = (
-                        f"{content}\n\n【系统提示】已对用户上传的图片完成火灾烟雾检测，"
-                        f"检测结果摘要如下（请不要再次调用检测工具）：\n{display_text}\n"
-                        f"请直接基于以上结果回复用户。"
-                    )
-
             # 调用 detection_agent.chat()（异步 → 同步）
             result = asyncio.run(detection_agent.chat(content, history))
 
             reply_content = result.get("output", "抱歉，无法处理您的请求。")
 
-            # 提取工具调用信息（Agent 可能基于系统提示不再调用检测工具）
+            # 提取工具调用信息
+            tool_calls = []
+            tool_result_str = ""
             intermediate_steps = result.get("intermediate_steps", [])
             for step in intermediate_steps:
                 action, observation = step
-                # 仅记录非检测类工具的调用，避免重复记录已预处理的图片检测
-                if action.tool != "detect_single_image":
-                    tool_calls.append({
-                        "tool": action.tool,
-                        "args": action.tool_input,
-                    })
-                    if isinstance(observation, str):
-                        tool_result_str += observation + "\n"
+                tool_calls.append({
+                    "tool": action.tool,
+                    "args": action.tool_input,
+                })
+                if isinstance(observation, str):
+                    tool_result_str += observation + "\n"
 
             latency_ms = int((time.time() - start_time) * 1000)
             tokens_used = max(1, (len(content) + len(reply_content) + len(tool_result_str)) // 2)
@@ -468,7 +437,7 @@
             logger.exception("ReAct Agent 执行失败")
             reply = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
             latency_ms = int((time.time() - start_time) * 1000)
-            return reply, tool_calls, tool_result_str.strip(), 0, latency_ms
+            return reply, [], "", 0, latency_ms
 
     # ══════════════════════════════════════════════════════════════
     # Stub 模式辅助方法
@@ -637,7 +606,6 @@
         将工具调用结果格式化为自然语言回复。
 
         模拟 Agent 在获得工具结果后，生成用户友好的回复。
-        如果 tool_result 是 detect_single_image 返回的 JSON，则提取 summary 字段展示。
 
         Args:
             user_message: 用户原始消息
@@ -662,34 +630,7 @@
 
         prefix = prefixes.get(tool_name, f"已为您执行{tool_description}，以下是结果：")
 
-        # 检测工具返回 JSON 时，优先展示 summary 文字，避免把 base64 输出到聊天正文
-        display_result = tool_result
-        if tool_name == "detect_single_image":
-            try:
-                parsed = json.loads(tool_result)
-                if isinstance(parsed, dict) and "summary" in parsed:
-                    display_result = parsed["summary"]
-            except json.JSONDecodeError:
-                pass
-
-        return f"{prefix}\n\n{display_result}"
-
-    @staticmethod
-    def _extract_tool_result_summary(tool_name: str, tool_result: str) -> str:
-        """
-        从工具结果中提取适合在聊天正文中展示的文字摘要。
-
-        对于 detect_single_image 返回的 JSON，提取 summary 字段，
-        避免将 base64 图片数据输出到聊天流中。
-        """
-        if tool_name == "detect_single_image":
-            try:
-                parsed = json.loads(tool_result)
-                if isinstance(parsed, dict) and "summary" in parsed:
-                    return parsed["summary"]
-            except json.JSONDecodeError:
-                pass
-        return tool_result
+        return f"{prefix}\n\n{tool_result}"
 
     @staticmethod
     def _build_stub_reply(content: str, history: list = None) -> str:
@@ -732,7 +673,7 @@
         - event: token, data: {content: "xxx"}
         - event: tool_call, data: {tool: "xxx", args: {...}}
         - event: done, data: {tokens_used, latency_ms, message_id, tool_calls, tool_result}
-        - event: error, data: {content: "xxx"}
+        - event: error, data: {message: "xxx"}
         """
         from app.database.session import SessionLocal
 
@@ -828,30 +769,23 @@
                             )
 
                             # 发送工具开始事件
-                            tool_start_data = {'tool': tool_name, 'input': tool_args}
+                            tool_start_data = {'tool': tool_name, 'args': tool_args}
                             yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                             yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
 
                             try:
                                 tool_result = self._invoke_tool_stub(tool_name, tool_args)
-                                json.loads(tool_result)  # 校验返回是否为有效 JSON
-                            except json.JSONDecodeError:
-                                logger.warning("SSE Stub 图片检测工具返回非 JSON 结果: %s", tool_result)
-                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
                             except Exception as e:
                                 logger.exception("SSE Stub 图片检测工具调用失败: %s", e)
-                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)
-
-                            # 发送工具结束事件（含完整结果，供前端解析标注图）
-                            tool_end_data = {'tool': tool_name, 'result': tool_result}
+                                tool_result = f"工具调用失败：{str(e)}"
+
+                            # 发送工具结束事件
+                            tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                             yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
 
-                            # 发送专用工具结果事件，前端可据此渲染 DetectionResultCard
-                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"
-
-                            # 发送文字摘要到聊天正文
-                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
-                            result_content = "\n\n" + display_text
+                            # 发送工具结果事件
+                            nl = "\n\n"
+                            result_content = nl + tool_result
                             yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                             yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
 
@@ -872,7 +806,7 @@
                         tool_calls = [{"tool": tool_name, "args": tool_args}]
 
                         # 发送工具开始事件（tool_start 新事件名，保留 tool_call 向后兼容）
-                        tool_start_data = {'tool': tool_name, 'input': tool_args}
+                        tool_start_data = {'tool': tool_name, 'args': tool_args}
                         yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                         yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
 
@@ -880,15 +814,15 @@
                             tool_result = self._invoke_tool_stub(tool_name, tool_args)
                         except Exception as e:
                             logger.exception("SSE Stub 工具调用失败: tool=%s", tool_name)
-                            tool_result = json.dumps({"error": f"工具调用失败：{str(e)}"}, ensure_ascii=False)
+                            tool_result = f"工具调用失败：{str(e)}"
 
                         # 发送工具结束事件（tool_end 新事件名）
                         tool_end_data = {'tool': tool_name, 'result': str(tool_result)[:500]}
                         yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
 
                         # 发送工具结果事件（text_chunk 新事件名，保留 token 向后兼容）
-                        display_text = self._extract_tool_result_summary(tool_name, tool_result)
-                        result_content = "\n\n" + display_text
+                        nl = "\n\n"
+                        result_content = nl + tool_result
                         yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
                         yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
 
@@ -915,52 +849,6 @@
                     tool_calls = []
                     tool_result = ""
 
-                    # 若用户上传了图片，先直接调用检测工具，避免把 base64 标注图
-                    # 送入 LLM 上下文导致 token 超限；只把文字摘要交给 Agent。
-                    if data.files and self._has_image_file(data.files):
-                        first_image_url = self._extract_first_image_url(data.files)
-                        if first_image_url:
-                            tool_name = "detect_single_image"
-                            tool_args = {"image_path": first_image_url, "conf": 0.25, "iou": 0.45}
-                            tool_calls.append({"tool": tool_name, "args": tool_args})
-
-                            tool_start_data = {"tool": tool_name, "input": tool_args}
-                            yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
-                            yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
-
-                            try:
-                                from app.agent.tools.detection_tool import detect_single_image
-                                loop = asyncio.get_event_loop()
-                                tool_result = await loop.run_in_executor(
-                                    None,
-                                    lambda: detect_single_image.invoke(tool_args),
-                                )
-                                json.loads(tool_result)  # 校验返回是否为有效 JSON
-                            except json.JSONDecodeError:
-                                logger.warning("真实模式图片检测工具返回非 JSON 结果: %s", tool_result)
-                                tool_result = json.dumps({"error": f"工具返回了非 JSON 结果：{tool_result}"}, ensure_ascii=False)
-                            except Exception as e:
-                                logger.exception("真实模式图片预处理检测失败")
-                                tool_result = json.dumps({"error": f"检测失败：{str(e)}"}, ensure_ascii=False)
-
-                            # 发送完整工具结果，前端可解析标注图
-                            tool_end_data = {"tool": tool_name, "result": tool_result}
-                            yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
-                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False)}\n\n"
-
-                            # 在聊天正文显示文字摘要
-                            display_text = self._extract_tool_result_summary(tool_name, tool_result)
-                            result_content = "\n\n" + display_text
-                            yield f"event: text_chunk\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
-                            yield f"event: token\ndata: {json.dumps({'content': result_content}, ensure_ascii=False)}\n\n"
-
-                            # 只把摘要注入 Agent 提示词，避免 base64 撑爆上下文
-                            agent_content = (
-                                f"{agent_content}\n\n【系统提示】已对用户上传的图片完成火灾烟雾检测，"
-                                f"检测结果摘要如下（请不要再次调用检测工具）：\n{display_text}\n"
-                                f"请直接基于以上结果回复用户。"
-                            )
-
                     async for event in detection_agent.chat_stream(agent_content, history):
                         event_type = event.get("type", "")
 
@@ -974,7 +862,7 @@
                             tool_name = event.get("tool", "")
                             tool_input = event.get("input", {})
                             tool_calls.append({"tool": tool_name, "args": tool_input})
-                            tool_start_data = {'tool': tool_name, 'input': tool_input}
+                            tool_start_data = {'tool': tool_name, 'args': tool_input}
                             yield f"event: tool_start\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
                             yield f"event: tool_call\ndata: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
 
@@ -983,26 +871,23 @@
                             tool_name = event.get("tool", "")
                             if tool_output:
                                 tool_result += str(tool_output) + "\n"
-                                # 发送完整工具结果，前端可解析标注图
-                                tool_end_data = {'tool': tool_name, 'result': tool_output}
+                                tool_end_data = {'tool': tool_name, 'result': str(tool_output)[:500]}
                                 yield f"event: tool_end\ndata: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
-                                yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': tool_output}, ensure_ascii=False)}\n\n"
 
                         elif event_type == "error":
-                            error_content = event.get("content", "") or event.get("message", "")
-                            if not error_content:
-                                error_content = "AI 服务暂时不可用，请稍后重试。"
-                            yield f"event: error\ndata: {json.dumps({'content': error_content}, ensure_ascii=False)}\n\n"
+                            error_content = event.get("content", "")
+                            yield f"event: error\ndata: {json.dumps({'message': error_content}, ensure_ascii=False)}\n\n"
 
                     if not full_content:
                         full_content = "抱歉，无法处理您的请求。"
 
                 except Exception as e:
                     logger.exception("SSE Agent 执行失败")
-                    full_content = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)}）"
+                    full_content = f"AI 服务暂时不可用，请稍后重试。"
                     tool_calls = []
                     tool_result = ""
-                    yield f"event: error\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"
+                    yield f"event: text_chunk\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"
+                    yield f"event: token\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"
 
             latency_ms = int((time.time() - start_time) * 1000)
             tokens_used = max(1, (len(data.content) + len(full_content)) // 2)
@@ -1042,7 +927,7 @@
         except Exception as e:
             db.rollback()
             logger.error("SSE流式输出错误: %s", e)
-            yield f"event: error\ndata: {json.dumps({'content': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
+            yield f"event: error\ndata: {json.dumps({'message': 'AI服务暂时不可用，请稍后重试'}, ensure_ascii=False)}\n\n"
         finally:
             db.close()
 
```
**结论**：恢复真实模式中的图片预处理、工具结果提取、错误 SSE 事件发送，并确保 SSE 字段统一。


---

### 文件：backend/app/services/detection_service.py
**优先级**：P0
**影响说明**：检测服务核心逻辑变化，影响模型加载、图像预处理、MinIO 上传、推理耗时统计、结果返回。
**备份版本（原功能）**：
```python
"""
检测服务模块

基于 YOLOv11 的火焰烟雾目标检测核心服务：
- 单图检测：上传图片 → 模型推理 → 标注 → 入库 → 火情判定 → 预警
- 批量检测：多张图片循环检测
- 视频检测：逐帧检测，支持跳帧
"""
import base64
import io
import json
import os
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch
from PIL import Image
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionResult, DetectionScene, DetectionTask, ModelVersion
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)


class DetectionService:
    """火灾烟雾检测服务，封装 YOLOv11 模型推理全流程"""

    MAX_CACHE_SIZE = 4

    def __init__(self):
        self._model_cache: OrderedDict[int, Any] = OrderedDict()
        self._lock = threading.Lock()

    def detect_single(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_file: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> DetectionTask:
        """单图检测完整流程"""
        minio_client = MinIOClient()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
        original_url = None
        # 1. 上传原图到 MinIO（非致命：上传失败不影响检测）
        try:
            original_url = minio_client.upload_bytes(image_file, object_name, f"image/{ext}")
        except Exception as upload_err:
            logger.warning("MinIO 原图上传失败，跳过存储继续检测: %s", upload_err)

        try:
            # 2. 加载场景默认模型
            model = self._load_model(db, scene_id)

            # 3. 执行推理（强制转为 RGB 避免 RGBA 四通道导致模型报错）
            # 注意：必须传 PIL Image 而非 numpy 数组，因为 YOLO 对 PIL Image 和 numpy
            # 数组的预处理路径不同，numpy 数组会导致检测结果全部为 0（P0 级 bug）
            image = Image.open(io.BytesIO(image_file)).convert("RGB")
            t_start = datetime.now()
            results = model(image, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)
            # 记录推理耗时（优先使用 YOLO speed 指标，兜底用 wall-clock 时间）
            inference_time = (
                results[0].speed.get("inference", 0) if hasattr(results[0], "speed") and results[0].speed
                else (datetime.now() - t_start).total_seconds() * 1000
            )

            # 4. 绘制检测框并上传标注图（非致命：上传失败不影响检测）
            annotated_image = results[0].plot()
            annotated_bytes = cv2.imencode(f".{ext}", annotated_image)[1].tobytes()
            annotated_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/annotated_{filename}"
            annotated_url = None
            try:
                annotated_url = minio_client.upload_bytes(annotated_bytes, annotated_object_name, f"image/{ext}")
            except Exception as upload_err:
                logger.warning("MinIO 标注图上传失败，跳过存储: %s", upload_err)

            # 5. 创建 DetectionTask 记录
            # 同时把标注图以 base64 形式附在对象上，供上层（如对话工具）在 MinIO
            # 上传失败时直接嵌入到回复中，避免丢失可视化结果。
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="single",
                file_name=filename,
                original_url=original_url,
                annotated_url=annotated_url,
                status="completed",
                image_width=image.width,
                image_height=image.height,
                detected_at=datetime.now(),
                total_inference_time=inference_time,
            )
            task.annotated_image_base64 = base64.b64encode(annotated_bytes).decode("utf-8")
            db.add(task)
            db.flush()

            # 6. 为每个检测目标创建 DetectionResult
            fire_count = 0
            smoke_count = 0
            fire_area_sum = 0.0
            smoke_area_sum = 0.0
            image_area = image.width * image.height

            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1
                area = w * h

                result = DetectionResult(
                    task_id=task.id,
                    image_path=original_url or object_name,
                    annotated_image_url=annotated_url,
                    class_name=cls_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=xyxy,
                    x_min=x1,
                    y_min=y1,
                    x_max=x2,
                    y_max=y2,
                    width=w,
                    height=h,
                    area=area,
                    image_width=image.width,
                    image_height=image.height,
                )
                db.add(result)

                if cls_name == "fire":
                    fire_count += 1
                    fire_area_sum += area
                elif cls_name == "smoke":
                    smoke_count += 1
                    smoke_area_sum += area

            # 7. 火情等级判定
            from app.services.fire_level_service import fire_level_service
            fire_level_result = fire_level_service.judge(
                fire_count=fire_count,
                smoke_count=smoke_count,
                fire_area=fire_area_sum / image_area if image_area > 0 else 0,
                smoke_area=smoke_area_sum / image_area if image_area > 0 else 0,
            )

            # 8. 更新 task 火情字段
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = fire_count
            task.smoke_object_count = smoke_count

            db.commit()
            db.refresh(task)

            # 9. 生成火灾预警（若需要）
            from app.services.alert_service import alert_service
            alert_service.create_alert(db, task, fire_level_result)

            logger.info(
                "单图检测完成: task_id=%s, fire_level=%s, fire_count=%d, smoke_count=%d",
                task.id, task.fire_level, fire_count, smoke_count,
            )
            return task
        except Exception as e:
            logger.exception("单图检测失败: filename=%s, error=%s", filename, e)
            # 回滚之前 flush 的半成品数据
            try:
                db.rollback()
            except Exception:
                pass
            # 尝试清理已上传的 MinIO 原图
            if original_url:
                try:
                    minio_client.delete_file(object_name)
                except Exception:
                    logger.warning("清理 MinIO 孤儿文件失败: %s", object_name)
            # 在新事务中创建 failed 状态记录
            try:
                error_task = DetectionTask(
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    file_name=filename,
                    original_url=None,
                    annotated_url=None,
                    status="failed",
                    error_message=str(e),
                    detected_at=datetime.now(),
                )
                db.add(error_task)
                db.commit()
                db.refresh(error_task)
                return error_task
            except Exception:
                logger.exception("创建失败任务记录也失败: filename=%s", filename)
                db.rollback()
                raise

    def detect_batch(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_files: List[bytes],
        filenames: List[str],
        **kwargs,
    ) -> List[DetectionTask]:
        """批量检测：使用线程池并发处理多张图片"""
        tasks: List[DetectionTask] = []

        def _detect_one(img_bytes: bytes, fname: str) -> Optional[DetectionTask]:
            """在独立线程中执行单图检测，使用独立 db session"""
            thread_db = SessionLocal()
            try:
                return self.detect_single(
                    thread_db, user_id, scene_id, img_bytes, fname, **kwargs
                )
            except Exception as exc:
                logger.error("批量检测中单个图片检测失败: filename=%s, error=%s", fname, exc)
                thread_db.rollback()
                return None
            finally:
                thread_db.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_detect_one, img_bytes, fname)
                for img_bytes, fname in zip(image_files, filenames)
            ]
            for f in futures:
                result = f.result()
                if result is not None:
                    tasks.append(result)
        return tasks

    def detect_video(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        video_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        frame_skip: int = 5,
    ) -> DetectionTask:
        """视频检测：逐帧检测，支持跳帧

        注意：此方法可能在 asyncio.to_thread 中运行，
        因此创建独立的 db session 以避免跨线程共享。
        """
        # 创建独立 session（线程安全）
        own_db = SessionLocal()
        try:
            minio_client = MinIOClient()
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
            object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
            # 上传视频到 MinIO
            video_url = minio_client.upload_bytes(video_bytes, object_name, f"video/{ext}")

            # 加载模型
            model = self._load_model(own_db, scene_id)

            # 读取视频
            temp_path = Path(settings.TRAIN_OUTPUT_DIR) / "temp" / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(video_bytes)

            output_path = temp_path.parent / f"output_{filename}"
            output_url = None

            # 先创建任务记录（status=processing），以便 Redis 进度追踪可使用 task.id
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="video",
                file_name=filename,
                original_url=video_url,
                annotated_url=None,
                status="processing",
                detected_at=datetime.now(),
            )
            own_db.add(task)
            own_db.commit()
            own_db.refresh(task)

            fps = 0.0
            total_frames = 0
            width = 0
            height = 0
            fire_frames: List[int] = []
            smoke_frames: List[int] = []
            total_fire_count = 0
            total_smoke_count = 0

            try:
                cap = cv2.VideoCapture(str(temp_path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # 初始化 Redis 进度追踪
                try:
                    import redis as redis_lib
                    redis_client = redis_lib.Redis(
                        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                        db=settings.REDIS_DB, decode_responses=True,
                    )
                    redis_client.set(
                        f"video:progress:{task.id}",
                        json.dumps({"progress": 0, "current_frame": 0, "total_frames": total_frames}),
                        ex=3600,
                    )
                except Exception:
                    redis_client = None

                # 创建输出视频
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(str(output_path), fourcc, fps / max(frame_skip, 1), (width, height))

                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_idx += 1

                    if frame_idx % frame_skip != 0:
                        out.write(frame)
                        continue

                    results = model(frame, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)
                    annotated_frame = results[0].plot()
                    out.write(annotated_frame)

                    for box in results[0].boxes:
                        cls_name = model.names[int(box.cls[0])]
                        if cls_name == "fire":
                            fire_frames.append(frame_idx)
                            total_fire_count += 1
                        elif cls_name == "smoke":
                            smoke_frames.append(frame_idx)
                            total_smoke_count += 1

                    # 更新 Redis 进度
                    if redis_client:
                        current_frame = frame_idx
                        try:
                            redis_client.set(
                                f"video:progress:{task.id}",
                                json.dumps({
                                    "progress": int((current_frame / total_frames) * 100),
                                    "current_frame": current_frame,
                                    "total_frames": total_frames,
                                }),
                                ex=3600,
                            )
                        except Exception:
                            pass

                cap.release()
                out.release()

                # 上传输出视频
                output_bytes = output_path.read_bytes()
                output_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/output_{filename}"
                output_url = minio_client.upload_bytes(output_bytes, output_object_name, f"video/{ext}")
            finally:
                if 'cap' in locals():
                    cap.release()
                if 'out' in locals():
                    out.release()
                if temp_path.exists():
                    os.remove(str(temp_path))
                if output_path.exists():
                    os.remove(str(output_path))

            # 火情等级判定
            from app.services.fire_level_service import fire_level_service
            fire_level_result = fire_level_service.judge(
                fire_count=total_fire_count,
                smoke_count=total_smoke_count,
                fire_area=len(fire_frames) / max(total_frames, 1),
                smoke_area=len(smoke_frames) / max(total_frames, 1),
            )

            # 更新任务为已完成状态
            task.annotated_url = output_url
            task.status = "completed"
            task.image_width = width
            task.image_height = height
            task.video_duration = total_frames / fps if fps > 0 else 0
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = total_fire_count
            task.smoke_object_count = total_smoke_count
            own_db.commit()
            own_db.refresh(task)

            # 清理 Redis 进度 key
            if redis_client:
                try:
                    redis_client.delete(f"video:progress:{task.id}")
                except Exception:
                    pass

            # 生成火灾预警
            from app.services.alert_service import alert_service
            alert_service.create_alert(own_db, task, fire_level_result)

            logger.info(
                "视频检测完成: task_id=%s, total_frames=%d, fire_frames=%d, smoke_frames=%d",
                task.id, total_frames, len(fire_frames), len(smoke_frames),
            )
            return task
        finally:
            own_db.close()

    def detect_zip(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        zip_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> List[DetectionTask]:
        """
        ZIP 批量检测：解压 ZIP 文件，对其中每张图片执行检测

        处理流程：
        1. 解压 ZIP 到内存
        2. 过滤出支持的图片格式（jpg/jpeg/png/bmp/webp）
        3. 对每张图片调用 detect_single 执行检测
        4. 返回所有检测任务列表

        Args:
            db: 数据库会话
            user_id: 用户 ID
            scene_id: 场景 ID
            zip_bytes: ZIP 文件字节数据
            filename: 原始 ZIP 文件名
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU 阈值
            image_size: 推理图像尺寸

        Returns:
            检测任务列表
        """
        import zipfile

        # ZIP 文件大小检查
        if len(zip_bytes) > settings.ZIP_MAX_SIZE_MB * 1024 * 1024:
            from fastapi import HTTPException as FastAPIHTTPException
            raise FastAPIHTTPException(
                status_code=413,
                detail=f"ZIP 文件超过最大限制 ({settings.ZIP_MAX_SIZE_MB} MB)",
            )

        # 支持的图片扩展名
        SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        tasks: List[DetectionTask] = []
        errors: List[dict] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                # 遍历 ZIP 中的所有文件
                file_list = [info for info in zf.infolist() if not info.is_dir()]
                logger.info(
                    "ZIP 检测开始: filename=%s, total_files=%d",
                    filename, len(file_list),
                )

                # 第一遍：收集所有图片文件信息
                image_files: List[tuple] = []  # (info, inner_name, ext)
                for info in file_list:
                    # 提取文件名（处理中文编码）
                    try:
                        inner_name = info.filename.encode("cp437").decode("gbk")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            inner_name = info.filename.encode("cp437").decode("utf-8")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            inner_name = info.filename

                    # 检查扩展名
                    ext = Path(inner_name).suffix.lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        logger.debug("跳过非图片文件: %s", inner_name)
                        continue

                    image_files.append((info, inner_name, ext))

                # 检查图片数量限制
                if len(image_files) > settings.ZIP_MAX_IMAGES:
                    from fastapi import HTTPException as FastAPIHTTPException
                    raise FastAPIHTTPException(
                        status_code=400,
                        detail=f"ZIP 包内图片数量超过限制 ({settings.ZIP_MAX_IMAGES} 张)",
                    )

                # 第二遍：逐张检测
                for info, inner_name, ext in image_files:
                    # 读取图片数据
                    try:
                        image_bytes = zf.read(info)
                        if not image_bytes:
                            continue

                        # 调用单图检测
                        task = self.detect_single(
                            db=db,
                            user_id=user_id,
                            scene_id=scene_id,
                            image_file=image_bytes,
                            filename=Path(inner_name).name or f"image{ext}",
                            conf_threshold=conf_threshold,
                            iou_threshold=iou_threshold,
                            image_size=image_size,
                        )
                        tasks.append(task)
                    except Exception as e:
                        logger.error("ZIP 中图片检测失败: %s, error=%s", inner_name, e)
                        errors.append({"file": inner_name, "error": str(e)})
                        continue

        except zipfile.BadZipFile as e:
            logger.error("ZIP 文件格式错误: %s", e)
            raise ValueError(f"无效的 ZIP 文件: {str(e)}") from e
        except Exception as e:
            logger.exception("ZIP 检测异常: filename=%s", filename)
            raise

        logger.info(
            "ZIP 检测完成: filename=%s, success=%d, errors=%d",
            filename, len(tasks), len(errors),
        )

        return tasks

    def detect_frame(
        self,
        frame_bytes: bytes,
        scene_id: int = 1,
        conf: float = 0.25,
        iou: float = 0.45,
        image_size: int = 640,
        device: str = "cpu",
    ) -> dict:
        """纯推理方法，用于WebSocket摄像头实时检测。无DB/MinIO操作。"""
        import base64

        # 1. 解码JPEG帧
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("无法解码帧图像")

        # 2. 加载模型（_load_model 支持 db=None 时使用缓存）
        model = self._load_model(None, scene_id)

        # 3. 推理
        results = model(frame, conf=conf, iou=iou, imgsz=image_size, device=device, save=False, verbose=False)

        # 4. 绘制标注框
        annotated = results[0].plot()

        # 5. 编码标注帧
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')

        # 6. 提取检测框信息
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": results[0].names[cls_id],
                "confidence": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),
            })

        # 统计 fire 和 smoke 数量
        fire_count = sum(1 for d in detections if d.get("class", "") == "fire")
        smoke_count = sum(1 for d in detections if d.get("class", "") == "smoke")

        # 火情等级判定
        fire_level = ""
        if fire_count >= 3:
            fire_level = "danger"
        elif fire_count >= 2:
            fire_level = "warning"
        elif fire_count >= 1:
            fire_level = "notice"

        return {
            "annotated_frame": annotated_b64,
            "detections": detections,
            "total_objects": len(detections),
            "fire_level": fire_level,
            "fire_count": fire_count,
            "smoke_count": smoke_count,
        }

    def _load_model(self, db: Optional[Session], scene_id: int):
        """加载场景默认模型（带 LRU 缓存，最大 MAX_CACHE_SIZE 个）
        
        当 db=None 时（如 detect_frame 纯推理场景），仅从缓存加载或使用默认模型。
        
        模型路径解析优先级：
        1. DB 中场景绑定的默认模型（db 不为 None 时）
        2. settings.DEFAULT_MODEL_PATH（相对于后端根目录解析）
        3. 后端根目录下的 yolo11n.pt（本地文件，不触发网络下载）
        4. 最后才尝试 YOLO("yolov11n.pt")（会触发网络下载，仅作兜底）
        """
        with self._lock:
            if scene_id in self._model_cache:
                # 移到末尾表示最近使用
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

        from ultralytics import YOLO

        # 后端根目录绝对路径：detection_service.py → services/ → app/ → backend/
        _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

        model_version = None
        if db is not None:
            # 查找场景默认模型版本
            model_version = (
                db.query(ModelVersion)
                .filter(ModelVersion.scene_id == scene_id, ModelVersion.is_default == True)
                .first()
            )

        with self._lock:
            # 确保模型使用确定性推理，避免 CPU 浮点非确定性导致结果随机波动
            torch.use_deterministic_algorithms(True, warn_only=True)

            # 加锁后再次检查，避免并发重复加载
            if scene_id in self._model_cache:
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

            if model_version and model_version.model_path and os.path.exists(model_version.model_path):
                logger.info("使用场景绑定模型: scene_id=%s, path=%s", scene_id, model_version.model_path)
                model = YOLO(model_version.model_path)
            elif settings.DEFAULT_MODEL_PATH:
                # 将 DEFAULT_MODEL_PATH 解析为绝对路径（相对于后端根目录）
                model_path = Path(settings.DEFAULT_MODEL_PATH)
                # 防御性兜底：如果 DEFAULT_MODEL_PATH 是通用 COCO 模型，自动切换到火灾烟雾专用模型
                if model_path.name in ("yolo11n.pt", "yolov11n.pt"):
                    fire_smoke_path = Path(settings.FIRE_SMOKE_MODEL_PATH)
                    if not fire_smoke_path.is_absolute():
                        fire_smoke_path = _BACKEND_ROOT / fire_smoke_path
                    if fire_smoke_path.exists():
                        logger.info("DEFAULT_MODEL_PATH 是通用模型，自动切换到火灾烟雾模型: %s", fire_smoke_path)
                        model_path = fire_smoke_path
                if not model_path.is_absolute():
                    model_path = _BACKEND_ROOT / model_path
                if model_path.exists():
                    logger.info("使用 DEFAULT_MODEL_PATH: %s", model_path)
                    model = YOLO(str(model_path))
                else:
                    # DEFAULT_MODEL_PATH 指定的文件不存在，尝试本地 yolo11n.pt
                    fallback = _BACKEND_ROOT / "yolo11n.pt"
                    if fallback.exists():
                        logger.warning("DEFAULT_MODEL_PATH 不存在(%s)，使用本地: %s", model_path, fallback)
                        model = YOLO(str(fallback))
                    else:
                        logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                        model = YOLO("yolov11n.pt")
            else:
                # 无 DEFAULT_MODEL_PATH，优先使用本地 yolo11n.pt（绝对路径，不触发下载）
                fallback = _BACKEND_ROOT / "yolo11n.pt"
                if fallback.exists():
                    logger.info("使用本地 yolo11n.pt: %s", fallback)
                    model = YOLO(str(fallback))
                else:
                    logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                    model = YOLO("yolov11n.pt")

            # LRU 淘汰：超出上限时移除最久未使用的模型
            if len(self._model_cache) >= self.MAX_CACHE_SIZE:
                oldest_key = next(iter(self._model_cache))
                del self._model_cache[oldest_key]
                logger.info("模型缓存已满，淘汰最旧模型: scene_id=%s", oldest_key)

            self._model_cache[scene_id] = model

        logger.info("检测模型已加载: scene_id=%s", scene_id)
        return model


# 单例
detection_service = DetectionService()
```
**当前版本（缺失/被改）**：
```python
"""
检测服务模块

基于 YOLOv11 的火焰烟雾目标检测核心服务：
- 单图检测：上传图片 → 模型推理 → 标注 → 入库 → 火情判定 → 预警
- 批量检测：多张图片循环检测
- 视频检测：逐帧检测，支持跳帧
"""
import base64
import io
import json
import os
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch
from PIL import Image
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionResult, DetectionScene, DetectionTask, ModelVersion
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)


class DetectionService:
    """火灾烟雾检测服务，封装 YOLOv11 模型推理全流程"""

    MAX_CACHE_SIZE = 4

    def __init__(self):
        self._model_cache: OrderedDict[int, Any] = OrderedDict()
        self._lock = threading.Lock()

    def detect_single(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_file: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> DetectionTask:
        """单图检测完整流程"""
        minio_client = MinIOClient()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
        original_url = None
        # 1. 上传原图到 MinIO（非致命：上传失败不影响检测）
        try:
            original_url = minio_client.upload_bytes(image_file, object_name, f"image/{ext}")
        except Exception as upload_err:
            logger.warning("MinIO 原图上传失败，跳过存储继续检测: %s", upload_err)

        try:
            # 2. 加载场景默认模型
            model = self._load_model(db, scene_id)

            # 3. 执行推理（强制转为 RGB 避免 RGBA 四通道导致模型报错）
            # 注意：必须传 PIL Image 而非 numpy 数组，因为 YOLO 对 PIL Image 和 numpy
            # 数组的预处理路径不同，numpy 数组会导致检测结果全部为 0（P0 级 bug）
            image = Image.open(io.BytesIO(image_file)).convert("RGB")
            t_start = datetime.now()
            results = model(image, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)
            # 记录推理耗时（优先使用 YOLO speed 指标，兜底用 wall-clock 时间）
            inference_time = (
                results[0].speed.get("inference", 0) if hasattr(results[0], "speed") and results[0].speed
                else (datetime.now() - t_start).total_seconds() * 1000
            )

            # 4. 绘制检测框并上传标注图（非致命：上传失败不影响检测）
            annotated_image = results[0].plot()
            annotated_bytes = cv2.imencode(f".{ext}", annotated_image)[1].tobytes()
            annotated_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/annotated_{filename}"
            annotated_url = None
            try:
                annotated_url = minio_client.upload_bytes(annotated_bytes, annotated_object_name, f"image/{ext}")
            except Exception as upload_err:
                logger.warning("MinIO 标注图上传失败，跳过存储: %s", upload_err)

            # 5. 创建 DetectionTask 记录
            # 同时把标注图以 base64 形式附在对象上，供上层（如对话工具）在 MinIO
            # 上传失败时直接嵌入到回复中，避免丢失可视化结果。
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="single",
                file_name=filename,
                original_url=original_url,
                annotated_url=annotated_url,
                status="completed",
                image_width=image.width,
                image_height=image.height,
                detected_at=datetime.now(),
                total_inference_time=inference_time,
            )
            task.annotated_image_base64 = base64.b64encode(annotated_bytes).decode("utf-8")
            db.add(task)
            db.flush()

            # 6. 为每个检测目标创建 DetectionResult
            fire_count = 0
            smoke_count = 0
            fire_area_sum = 0.0
            smoke_area_sum = 0.0
            image_area = image.width * image.height

            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                x1, y1, x2, y2 = xyxy
                w = x2 - x1
                h = y2 - y1
                area = w * h

                result = DetectionResult(
                    task_id=task.id,
                    image_path=original_url or object_name,
                    annotated_image_url=annotated_url,
                    class_name=cls_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=xyxy,
                    x_min=x1,
                    y_min=y1,
                    x_max=x2,
                    y_max=y2,
                    width=w,
                    height=h,
                    area=area,
                    image_width=image.width,
                    image_height=image.height,
                )
                db.add(result)

                if cls_name == "fire":
                    fire_count += 1
                    fire_area_sum += area
                elif cls_name == "smoke":
                    smoke_count += 1
                    smoke_area_sum += area

            # 7. 火情等级判定
            from app.services.fire_level_service import fire_level_service
            fire_level_result = fire_level_service.judge(
                fire_count=fire_count,
                smoke_count=smoke_count,
                fire_area=fire_area_sum / image_area if image_area > 0 else 0,
                smoke_area=smoke_area_sum / image_area if image_area > 0 else 0,
            )

            # 8. 更新 task 火情字段
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = fire_count
            task.smoke_object_count = smoke_count

            db.commit()
            db.refresh(task)

            # 9. 生成火灾预警（若需要）
            from app.services.alert_service import alert_service
            alert_service.create_alert(db, task, fire_level_result)

            logger.info(
                "单图检测完成: task_id=%s, fire_level=%s, fire_count=%d, smoke_count=%d",
                task.id, task.fire_level, fire_count, smoke_count,
            )
            return task
        except Exception as e:
            logger.exception("单图检测失败: filename=%s, error=%s", filename, e)
            # 回滚之前 flush 的半成品数据
            try:
                db.rollback()
            except Exception:
                pass
            # 尝试清理已上传的 MinIO 原图
            if original_url:
                try:
                    minio_client.delete_file(object_name)
                except Exception:
                    logger.warning("清理 MinIO 孤儿文件失败: %s", object_name)
            # 在新事务中创建 failed 状态记录
            try:
                error_task = DetectionTask(
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    file_name=filename,
                    original_url=None,
                    annotated_url=None,
                    status="failed",
                    error_message=str(e),
                    detected_at=datetime.now(),
                )
                db.add(error_task)
                db.commit()
                db.refresh(error_task)
                return error_task
            except Exception:
                logger.exception("创建失败任务记录也失败: filename=%s", filename)
                db.rollback()
                raise

    def detect_batch(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        image_files: List[bytes],
        filenames: List[str],
        **kwargs,
    ) -> List[DetectionTask]:
        """批量检测：使用线程池并发处理多张图片"""
        tasks: List[DetectionTask] = []

        def _detect_one(img_bytes: bytes, fname: str) -> Optional[DetectionTask]:
            """在独立线程中执行单图检测，使用独立 db session"""
            thread_db = SessionLocal()
            try:
                return self.detect_single(
                    thread_db, user_id, scene_id, img_bytes, fname, **kwargs
                )
            except Exception as exc:
                logger.error("批量检测中单个图片检测失败: filename=%s, error=%s", fname, exc)
                thread_db.rollback()
                return None
            finally:
                thread_db.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_detect_one, img_bytes, fname)
                for img_bytes, fname in zip(image_files, filenames)
            ]
            for f in futures:
                result = f.result()
                if result is not None:
                    tasks.append(result)
        return tasks

    def detect_video(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        video_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        frame_skip: int = 5,
    ) -> DetectionTask:
        """视频检测：逐帧检测，支持跳帧

        注意：此方法可能在 asyncio.to_thread 中运行，
        因此创建独立的 db session 以避免跨线程共享。
        """
        # 创建独立 session（线程安全）
        own_db = SessionLocal()
        try:
            minio_client = MinIOClient()
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
            object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/{filename}"
            # 上传视频到 MinIO
            video_url = minio_client.upload_bytes(video_bytes, object_name, f"video/{ext}")

            # 加载模型
            model = self._load_model(own_db, scene_id)

            # 读取视频
            temp_path = Path(settings.TRAIN_OUTPUT_DIR) / "temp" / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(video_bytes)

            output_path = temp_path.parent / f"output_{filename}"
            output_url = None

            # 先创建任务记录（status=processing），以便 Redis 进度追踪可使用 task.id
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_type="video",
                file_name=filename,
                original_url=video_url,
                annotated_url=None,
                status="processing",
                detected_at=datetime.now(),
            )
            own_db.add(task)
            own_db.commit()
            own_db.refresh(task)

            fps = 0.0
            total_frames = 0
            width = 0
            height = 0
            fire_frames: List[int] = []
            smoke_frames: List[int] = []
            total_fire_count = 0
            total_smoke_count = 0

            try:
                cap = cv2.VideoCapture(str(temp_path))
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # 初始化 Redis 进度追踪
                try:
                    import redis as redis_lib
                    redis_client = redis_lib.Redis(
                        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                        db=settings.REDIS_DB, decode_responses=True,
                    )
                    redis_client.set(
                        f"video:progress:{task.id}",
                        json.dumps({"progress": 0, "current_frame": 0, "total_frames": total_frames}),
                        ex=3600,
                    )
                except Exception:
                    redis_client = None

                # 创建输出视频
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(str(output_path), fourcc, fps / max(frame_skip, 1), (width, height))

                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_idx += 1

                    if frame_idx % frame_skip != 0:
                        out.write(frame)
                        continue

                    results = model(frame, conf=conf_threshold, iou=iou_threshold, imgsz=image_size)
                    annotated_frame = results[0].plot()
                    out.write(annotated_frame)

                    for box in results[0].boxes:
                        cls_name = model.names[int(box.cls[0])]
                        if cls_name == "fire":
                            fire_frames.append(frame_idx)
                            total_fire_count += 1
                        elif cls_name == "smoke":
                            smoke_frames.append(frame_idx)
                            total_smoke_count += 1

                    # 更新 Redis 进度
                    if redis_client:
                        current_frame = frame_idx
                        try:
                            redis_client.set(
                                f"video:progress:{task.id}",
                                json.dumps({
                                    "progress": int((current_frame / total_frames) * 100),
                                    "current_frame": current_frame,
                                    "total_frames": total_frames,
                                }),
                                ex=3600,
                            )
                        except Exception:
                            pass

                cap.release()
                out.release()

                # 上传输出视频
                output_bytes = output_path.read_bytes()
                output_object_name = f"detection/{user_id}/{datetime.now().strftime('%Y%m%d')}/output_{filename}"
                output_url = minio_client.upload_bytes(output_bytes, output_object_name, f"video/{ext}")
            finally:
                if 'cap' in locals():
                    cap.release()
                if 'out' in locals():
                    out.release()
                if temp_path.exists():
                    os.remove(str(temp_path))
                if output_path.exists():
                    os.remove(str(output_path))

            # 火情等级判定
            from app.services.fire_level_service import fire_level_service
            fire_level_result = fire_level_service.judge(
                fire_count=total_fire_count,
                smoke_count=total_smoke_count,
                fire_area=len(fire_frames) / max(total_frames, 1),
                smoke_area=len(smoke_frames) / max(total_frames, 1),
            )

            # 更新任务为已完成状态
            task.annotated_url = output_url
            task.status = "completed"
            task.image_width = width
            task.image_height = height
            task.video_duration = total_frames / fps if fps > 0 else 0
            task.fire_level = fire_level_result["fire_level"]
            task.risk_level = fire_level_result["fire_level"]
            task.fire_area = fire_level_result["fire_area"]
            task.smoke_area = fire_level_result["smoke_area"]
            task.fire_object_count = total_fire_count
            task.smoke_object_count = total_smoke_count
            own_db.commit()
            own_db.refresh(task)

            # 清理 Redis 进度 key
            if redis_client:
                try:
                    redis_client.delete(f"video:progress:{task.id}")
                except Exception:
                    pass

            # 生成火灾预警
            from app.services.alert_service import alert_service
            alert_service.create_alert(own_db, task, fire_level_result)

            logger.info(
                "视频检测完成: task_id=%s, total_frames=%d, fire_frames=%d, smoke_frames=%d",
                task.id, total_frames, len(fire_frames), len(smoke_frames),
            )
            return task
        finally:
            own_db.close()

    def detect_zip(
        self,
        db: Session,
        user_id: int,
        scene_id: int,
        zip_bytes: bytes,
        filename: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> List[DetectionTask]:
        """
        ZIP 批量检测：解压 ZIP 文件，对其中每张图片执行检测

        处理流程：
        1. 解压 ZIP 到内存
        2. 过滤出支持的图片格式（jpg/jpeg/png/bmp/webp）
        3. 对每张图片调用 detect_single 执行检测
        4. 返回所有检测任务列表

        Args:
            db: 数据库会话
            user_id: 用户 ID
            scene_id: 场景 ID
            zip_bytes: ZIP 文件字节数据
            filename: 原始 ZIP 文件名
            conf_threshold: 置信度阈值
            iou_threshold: NMS IoU 阈值
            image_size: 推理图像尺寸

        Returns:
            检测任务列表
        """
        import zipfile

        # ZIP 文件大小检查
        if len(zip_bytes) > settings.ZIP_MAX_SIZE_MB * 1024 * 1024:
            from fastapi import HTTPException as FastAPIHTTPException
            raise FastAPIHTTPException(
                status_code=413,
                detail=f"ZIP 文件超过最大限制 ({settings.ZIP_MAX_SIZE_MB} MB)",
            )

        # 支持的图片扩展名
        SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        tasks: List[DetectionTask] = []
        errors: List[dict] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                # 遍历 ZIP 中的所有文件
                file_list = [info for info in zf.infolist() if not info.is_dir()]
                logger.info(
                    "ZIP 检测开始: filename=%s, total_files=%d",
                    filename, len(file_list),
                )

                # 第一遍：收集所有图片文件信息
                image_files: List[tuple] = []  # (info, inner_name, ext)
                for info in file_list:
                    # 提取文件名（处理中文编码）
                    try:
                        inner_name = info.filename.encode("cp437").decode("gbk")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        try:
                            inner_name = info.filename.encode("cp437").decode("utf-8")
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            inner_name = info.filename

                    # 检查扩展名
                    ext = Path(inner_name).suffix.lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        logger.debug("跳过非图片文件: %s", inner_name)
                        continue

                    image_files.append((info, inner_name, ext))

                # 检查图片数量限制
                if len(image_files) > settings.ZIP_MAX_IMAGES:
                    from fastapi import HTTPException as FastAPIHTTPException
                    raise FastAPIHTTPException(
                        status_code=400,
                        detail=f"ZIP 包内图片数量超过限制 ({settings.ZIP_MAX_IMAGES} 张)",
                    )

                # 第二遍：逐张检测
                for info, inner_name, ext in image_files:
                    # 读取图片数据
                    try:
                        image_bytes = zf.read(info)
                        if not image_bytes:
                            continue

                        # 调用单图检测
                        task = self.detect_single(
                            db=db,
                            user_id=user_id,
                            scene_id=scene_id,
                            image_file=image_bytes,
                            filename=Path(inner_name).name or f"image{ext}",
                            conf_threshold=conf_threshold,
                            iou_threshold=iou_threshold,
                            image_size=image_size,
                        )
                        tasks.append(task)
                    except Exception as e:
                        logger.error("ZIP 中图片检测失败: %s, error=%s", inner_name, e)
                        errors.append({"file": inner_name, "error": str(e)})
                        continue

        except zipfile.BadZipFile as e:
            logger.error("ZIP 文件格式错误: %s", e)
            raise ValueError(f"无效的 ZIP 文件: {str(e)}") from e
        except Exception as e:
            logger.exception("ZIP 检测异常: filename=%s", filename)
            raise

        logger.info(
            "ZIP 检测完成: filename=%s, success=%d, errors=%d",
            filename, len(tasks), len(errors),
        )

        return tasks

    def detect_frame(
        self,
        frame_bytes: bytes,
        scene_id: int = 1,
        conf: float = 0.25,
        iou: float = 0.45,
        image_size: int = 640,
        device: str = "cpu",
    ) -> dict:
        """纯推理方法，用于WebSocket摄像头实时检测。无DB/MinIO操作。"""
        import base64

        # 1. 解码JPEG帧
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("无法解码帧图像")

        # 2. 加载模型（_load_model 支持 db=None 时使用缓存）
        model = self._load_model(None, scene_id)

        # 3. 推理
        results = model(frame, conf=conf, iou=iou, imgsz=image_size, device=device, save=False, verbose=False)

        # 4. 绘制标注框
        annotated = results[0].plot()

        # 5. 编码标注帧
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')

        # 6. 提取检测框信息
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": results[0].names[cls_id],
                "confidence": float(box.conf[0]),
                "bbox": box.xyxy[0].tolist(),
            })

        # 统计 fire 和 smoke 数量
        fire_count = sum(1 for d in detections if d.get("class", "") == "fire")
        smoke_count = sum(1 for d in detections if d.get("class", "") == "smoke")

        # 火情等级判定
        fire_level = ""
        if fire_count >= 3:
            fire_level = "danger"
        elif fire_count >= 2:
            fire_level = "warning"
        elif fire_count >= 1:
            fire_level = "notice"

        return {
            "annotated_frame": annotated_b64,
            "detections": detections,
            "total_objects": len(detections),
            "fire_level": fire_level,
            "fire_count": fire_count,
            "smoke_count": smoke_count,
        }

    def _load_model(self, db: Optional[Session], scene_id: int):
        """加载场景默认模型（带 LRU 缓存，最大 MAX_CACHE_SIZE 个）
        
        当 db=None 时（如 detect_frame 纯推理场景），仅从缓存加载或使用默认模型。
        
        模型路径解析优先级：
        1. DB 中场景绑定的默认模型（db 不为 None 时）
        2. settings.DEFAULT_MODEL_PATH（相对于后端根目录解析）
        3. 后端根目录下的 yolo11n.pt（本地文件，不触发网络下载）
        4. 最后才尝试 YOLO("yolov11n.pt")（会触发网络下载，仅作兜底）
        """
        with self._lock:
            if scene_id in self._model_cache:
                # 移到末尾表示最近使用
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

        from ultralytics import YOLO

        # 后端根目录绝对路径：detection_service.py → services/ → app/ → backend/
        _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

        model_version = None
        if db is not None:
            # 查找场景默认模型版本
            model_version = (
                db.query(ModelVersion)
                .filter(ModelVersion.scene_id == scene_id, ModelVersion.is_default == True)
                .first()
            )

        with self._lock:
            # 加锁后再次检查，避免并发重复加载
            if scene_id in self._model_cache:
                self._model_cache.move_to_end(scene_id)
                return self._model_cache[scene_id]

            if model_version and model_version.model_path and os.path.exists(model_version.model_path):
                logger.info("使用场景绑定模型: scene_id=%s, path=%s", scene_id, model_version.model_path)
                model = YOLO(model_version.model_path)
            elif settings.DEFAULT_MODEL_PATH:
                # 将 DEFAULT_MODEL_PATH 解析为绝对路径（相对于后端根目录）
                model_path = Path(settings.DEFAULT_MODEL_PATH)
                # 防御性兜底：如果 DEFAULT_MODEL_PATH 是通用 COCO 模型，自动切换到火灾烟雾专用模型
                if model_path.name in ("yolo11n.pt", "yolov11n.pt"):
                    fire_smoke_path = Path(settings.FIRE_SMOKE_MODEL_PATH)
                    if not fire_smoke_path.is_absolute():
                        fire_smoke_path = _BACKEND_ROOT / fire_smoke_path
                    if fire_smoke_path.exists():
                        logger.info("DEFAULT_MODEL_PATH 是通用模型，自动切换到火灾烟雾模型: %s", fire_smoke_path)
                        model_path = fire_smoke_path
                if not model_path.is_absolute():
                    model_path = _BACKEND_ROOT / model_path
                if model_path.exists():
                    logger.info("使用 DEFAULT_MODEL_PATH: %s", model_path)
                    model = YOLO(str(model_path))
                else:
                    # DEFAULT_MODEL_PATH 指定的文件不存在，尝试本地 yolo11n.pt
                    fallback = _BACKEND_ROOT / "yolo11n.pt"
                    if fallback.exists():
                        logger.warning("DEFAULT_MODEL_PATH 不存在(%s)，使用本地: %s", model_path, fallback)
                        model = YOLO(str(fallback))
                    else:
                        logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                        model = YOLO("yolov11n.pt")
            else:
                # 无 DEFAULT_MODEL_PATH，优先使用本地 yolo11n.pt（绝对路径，不触发下载）
                fallback = _BACKEND_ROOT / "yolo11n.pt"
                if fallback.exists():
                    logger.info("使用本地 yolo11n.pt: %s", fallback)
                    model = YOLO(str(fallback))
                else:
                    logger.warning("本地模型文件不存在，尝试下载 yolov11n.pt")
                    model = YOLO("yolov11n.pt")

            # LRU 淘汰：超出上限时移除最久未使用的模型
            if len(self._model_cache) >= self.MAX_CACHE_SIZE:
                oldest_key = next(iter(self._model_cache))
                del self._model_cache[oldest_key]
                logger.info("模型缓存已满，淘汰最旧模型: scene_id=%s", oldest_key)

            self._model_cache[scene_id] = model

        logger.info("检测模型已加载: scene_id=%s", scene_id)
        return model


# 单例
detection_service = DetectionService()
```
**统一差异（unified diff）**：
```diff
--- backup/backend/app/services/detection_service.py
+++ current/backend/app/services/detection_service.py
@@ -661,9 +661,6 @@
             )
 
         with self._lock:
-            # 确保模型使用确定性推理，避免 CPU 浮点非确定性导致结果随机波动
-            torch.use_deterministic_algorithms(True, warn_only=True)
-
             # 加锁后再次检查，避免并发重复加载
             if scene_id in self._model_cache:
                 self._model_cache.move_to_end(scene_id)
```
**结论**：确认使用火灾烟雾模型路径、PIL Image 传入 YOLO、MinIO 直接下载、失败降级逻辑。


---

### 文件：frontend/src/views/ChatPage.vue
**优先级**：P0
**影响说明**：智能对话页面核心逻辑变化，影响 SSE 事件解析、工具结果展示、错误处理、图片上传与多轮对话。
**备份版本（原功能）**：
```vue
<template>
  <div class="chat-page">
    <!-- ── 左侧会话列表 ── -->
    <ChatSidebar
      :sessions="agentStore.sessions"
      :current-session-id="agentStore.currentSessionId"
      @new-chat="handleNewSession"
      @switch-session="handleSwitchSession"
      @delete-session="handleDeleteSession"
      @rename-session="handleRenameSession"
    />

    <!-- ── 主对话区域 ── -->
    <div class="chat-main">
      <!-- 顶部栏：当前会话标题 + 操作 -->
      <div class="chat-header">
        <div class="header-left">
          <span class="header-title">{{ currentSessionTitle }}</span>
        </div>
        <div class="header-actions">
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('single')"
          >
            📷 单图检测
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('batch')"
          >
            📁 批量/ZIP
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleVideoDetect"
          >
            🎬 视频
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <!-- 欢迎消息（无会话时） -->
        <div v-if="agentStore.messages.length === 0" class="welcome-area">
          <div class="welcome-icon">
            <el-icon :size="56"><ChatDotRound /></el-icon>
          </div>
          <h2>你好！我是火灾烟雾智能检测智能体</h2>
          <p class="welcome-desc">上传图片或视频，我可以帮你检测火情和烟雾目标</p>
          <div class="welcome-tips">
            <div class="tip-item" @click="inputTextPlaceholder = '检测一下这张图片中的火情'">
              <el-icon><Picture /></el-icon>
              <span>图片检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '帮我分析这段视频中的烟雾'">
              <el-icon><VideoCamera /></el-icon>
              <span>视频检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '批量检测这个 ZIP 中的图片'">
              <el-icon><Folder /></el-icon>
              <span>批量检测</span>
            </div>
          </div>
        </div>

        <!-- 消息项 -->
        <div
          v-for="(msg, index) in agentStore.messages"
          :key="index"
          :class="['message-item', `message-${msg.role}`]"
        >
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message-wrapper message-user-wrapper">
            <div class="message-bubble user-bubble">
              <div v-if="msg.content" class="message-content">{{ msg.content }}</div>
              <!-- 单张图片附件 -->
              <div v-if="msg.imagePreview" class="message-attachment">
                <img :src="msg.imagePreview" alt="附件图片" />
              </div>
              <!-- 多图附件 -->
              <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
                <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
              </div>
            </div>
          </div>

          <!-- AI 消息 -->
          <div v-else-if="msg.role === 'assistant'" class="message-wrapper message-assistant-wrapper">
            <div class="message-bubble assistant-bubble">
              <!-- 思考中动画 -->
              <div v-if="msg.thinking" class="thinking-indicator">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
                <span class="thinking-text">{{ msg.thinkingContent || '正在思考中...' }}</span>
              </div>

              <!-- 打字中动画 -->
              <div v-else-if="msg.loading && !msg.thinking" class="typing-indicator">
                <span></span><span></span><span></span>
              </div>

              <!-- Markdown 渲染 -->
              <div
                v-if="!msg.loading && msg.content && !msg.thinking"
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <!-- 流式文本 -->
              <div
                v-if="msg.loading && msg.content && !msg.thinking"
                class="message-content streaming-text"
              >{{ msg.content }}</div>

              <!-- 工具调用时间线 -->
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-timeline">
                <div
                  v-for="(tc, tIdx) in msg.toolCalls"
                  :key="tIdx"
                  :class="['tool-timeline-item', `tool-status-${tc.status}`]"
                >
                  <div v-if="tc.status === 'running'" class="tool-loading">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>正在调用工具：{{ tc.tool }}</span>
                  </div>
                  <div v-else-if="tc.status === 'completed'" class="tool-completed">
                    <el-icon color="#67c23a"><CircleCheck /></el-icon>
                    <span>工具 {{ tc.tool }} 执行完成</span>
                    <el-popover
                      v-if="tc.resultSummary"
                      placement="right"
                      :width="300"
                      trigger="click"
                    >
                      <template #reference>
                        <el-button text size="small" type="primary">查看详情</el-button>
                      </template>
                      <div class="tool-result-detail">{{ tc.resultSummary }}</div>
                    </el-popover>
                  </div>
                  <div v-else-if="tc.status === 'failed'" class="tool-failed">
                    <el-icon color="#f56c6c"><CircleClose /></el-icon>
                    <span>工具 {{ tc.tool }} 调用失败</span>
                  </div>
                </div>
              </div>

              <!-- 错误 + 重试 -->
              <div v-if="msg.error" class="error-actions">
                <el-button type="warning" size="small" @click="retryLastMessage">
                  <el-icon><Refresh /></el-icon> 重试
                </el-button>
              </div>

              <!-- 检测结果卡片 -->
              <DetectionResultCard
                v-if="msg.detectionResult"
                :result="msg.detectionResult"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <ChatInput
        :disabled="agentStore.isLoading"
        @send="handleSend"
        @stop="handleStop"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 豆包风格全屏聊天界面
 *
 * 功能：
 *   - 左侧会话列表（可折叠）
 *   - 消息气泡（用户/AI 区分，Markdown 渲染）
 *   - 完整 SSE 事件协议（thinking/tool_start/tool_end/text_chunk/done/error）
 *   - 检测结果卡片 + 工具调用时间线
 *   - 快捷操作（单图/批量/视频检测）
 *   - 拖拽文件 + 文字输入 + 发送
 *   - 重试、停止生成
 */
import ChatInput from '@/components/chat/ChatInput.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { useAgentStore } from '@/stores/agent'
import request from '@/utils/request'
import { renderMarkdown } from '@/utils/markdown'
import { streamChat } from '@/utils/stream'
import { detectBatch, detectSingle, detectVideo, detectZip, getVideoStatus } from '@/api/detection'
import { ChatDotRound, CircleCheck, CircleClose, Folder, Loading, Picture, Refresh, VideoCamera } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref } from 'vue'

// ── Store ──
const agentStore = useAgentStore()

// ── 响应式状态 ──
const messageListRef = ref(null)
const inputTextPlaceholder = ref('')

// 重试用
const lastSentMessage = ref('')
const lastSentImage = ref(null)
const lastSentFiles = ref([])

// ── 计算属性 ──
const currentSessionTitle = computed(() => {
  if (!agentStore.currentSessionId) return '新对话'
  const session = agentStore.sessions.find((s) => s.id === agentStore.currentSessionId)
  return session?.title || '新对话'
})

// ── 会话管理 ──
function handleNewSession() {
  agentStore.newChat()
}

async function handleSwitchSession(sessionId) {
  await agentStore.switchSession(sessionId)
  scrollToBottom()
}

async function handleDeleteSession(sessionId) {
  await agentStore.deleteSession(sessionId)
}

async function handleRenameSession(sessionId, title) {
  try {
    await agentStore.renameSession(sessionId, title)
    ElMessage.success('重命名成功')
  } catch (err) {
    ElMessage.error('重命名失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
  }
}

// ── 发送消息 ──
async function handleSend({ text, files }) {
  if (!text && (!files || files.length === 0)) return

  const message = text || ''
  let uploadedFiles = []

  // Step 1: 如果有文件，先上传到后端
  if (files && files.length > 0) {
    ElMessage.info(`正在上传 ${files.length} 个文件...`)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const res = await request.post('/chat/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        uploadedFiles.push(res.data) // {url, type, name}
      }
      ElMessage.success(`文件上传完成 (${uploadedFiles.length} 个)`)
    } catch (err) {
      ElMessage.error('文件上传失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
      return
    }
  }

  // Step 2: 添加用户消息（含文件预览）
  lastSentMessage.value = message
  lastSentImage.value = (files && files.length > 0) ? files[0] : null
  lastSentFiles.value = uploadedFiles

  const userMsg = {
    role: 'user',
    content: message,
  }

  if (files && files.length > 0) {
    const imageFiles = files.filter(f => f.type?.startsWith('image/'))
    // 单张图片预览
    if (imageFiles.length === 1) {
      userMsg.image = imageFiles[0].name
      userMsg.imagePreview = URL.createObjectURL(imageFiles[0])
    }
    // 多图预览
    else if (imageFiles.length > 1) {
      userMsg.images = imageFiles.map(f => URL.createObjectURL(f))
    }
    // 如果只有非图片文件且没有文字，用文件名填充消息内容
    if (imageFiles.length < files.length && !message) {
      const fileNames = files.map(f => f.name).join(', ')
      userMsg.content = `[文件] ${fileNames}`
    }
  }

  agentStore.addMessage(userMsg)

  // Step 3: 添加 AI 加载占位
  agentStore.addMessage({
    role: 'assistant',
    content: '',
    loading: true,
    toolCalls: [],
  })

  agentStore.setLoading(true)
  scrollToBottom()

  // Step 4: 构造请求体并发起 SSE
  const requestBody = { content: message }
  if (uploadedFiles.length > 0) {
    requestBody.files = uploadedFiles
  }
  if (agentStore.currentSessionId) {
    requestBody.session_id = agentStore.currentSessionId
  }

  let fullContent = ''

  const stop = streamChat('/api/chat/messages/stream', requestBody, {
    onMessage: (data) => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (!lastMsg) return

      switch (data.type) {
        case 'thinking':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          lastMsg.thinking = true
          lastMsg.thinkingContent = data.content || '正在分析问题...'
          lastMsg.loading = true
          break

        case 'tool_start': {
          lastMsg.thinking = false
          lastMsg.loading = true
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool || '未知工具',
            input: data.input || data.args,
            status: 'running',
            startTime: Date.now(),
          })
          break
        }

        case 'tool_end': {
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
              try {
                const result = data.result ? JSON.parse(data.result) : {}
                if (result.error) {
                  runningTc.status = 'failed'
                  runningTc.resultSummary = result.error
                  const errorText = `检测失败：${result.error}`
                  lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
                  lastMsg.loading = false
                } else if (Array.isArray(result.detections)) {
                  runningTc.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
                  lastMsg.detectionResult = result
                  lastMsg.loading = false
                } else {
                  runningTc.resultSummary = JSON.stringify(result).substring(0, 200)
                }
              } catch (parseErr) {
                runningTc.status = 'failed'
                runningTc.resultSummary = (data.result || '').substring(0, 200)
                const failText = '工具结果解析失败，请稍后重试'
                lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${failText}` : failText
                lastMsg.loading = false
                console.error('[tool_end] 解析失败:', parseErr, data.result)
              }
            }
          }
          lastMsg.toolCall = { tool: data.tool, result: data.result }
          break
        }

        case 'text_chunk':
          lastMsg.thinking = false
          lastMsg.loading = true
          fullContent += data.content || ''
          lastMsg.content = fullContent
          break

        case 'done':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          if (data.response && !fullContent) {
            lastMsg.content = data.response
          }
          lastMsg.loading = false
          lastMsg.thinking = false
          agentStore.setLoading(false)
          agentStore.fetchSessions()
          break

        case 'error':
          lastMsg.content = data.content || '处理请求时发生错误'
          lastMsg.loading = false
          lastMsg.thinking = false
          lastMsg.error = true
          agentStore.setLoading(false)
          break

        case 'tool_call':
          lastMsg.thinking = false
          lastMsg.loading = true
          lastMsg.toolCall = { tool: data.tool, input: data.input || data.args }
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool,
            input: data.input || data.args,
            status: 'running',
            startTime: Date.now(),
          })
          break

        case 'tool_result': {
          let toolResult = null
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
              toolResult = runningTc
            }
          }
          try {
            const result = data.result ? JSON.parse(data.result) : {}
            if (result.error) {
              if (toolResult) toolResult.status = 'failed'
              const errorText = `检测失败：${result.error}`
              lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
              lastMsg.loading = false
            } else if (Array.isArray(result.detections)) {
              if (toolResult) {
                toolResult.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
              }
              lastMsg.detectionResult = result
              lastMsg.loading = false
            } else if (toolResult) {
              toolResult.resultSummary = JSON.stringify(result).substring(0, 200)
            }
          } catch (parseErr) {
            if (toolResult) toolResult.status = 'failed'
            if (toolResult) toolResult.resultSummary = (data.result || '').substring(0, 200)
            const failText = '工具结果解析失败，请稍后重试'
            lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${failText}` : failText
            lastMsg.loading = false
            console.error('[tool_result] 解析失败:', parseErr, data.result)
          }
          break
        }

        default:
          if (data.content) {
            lastMsg.thinking = false
            lastMsg.loading = true
            fullContent += data.content
            lastMsg.content = fullContent
          }
          break
      }

      scrollToBottom()
    },

    onDone: () => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        if (lastMsg.loading && !lastMsg.content && !lastMsg.detectionResult) {
          lastMsg.content = '处理完成。'
        }
        lastMsg.loading = false
        lastMsg.thinking = false
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      scrollToBottom()
    },

    onError: (err) => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `抱歉，处理出错了：${err.message}`
        lastMsg.loading = false
        lastMsg.thinking = false
        lastMsg.error = true
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      ElMessage.error('对话请求失败，请重试')
    },
  })

  agentStore.abortController = stop
}

// ── 重试 ──
async function retryLastMessage() {
  if (!lastSentMessage.value && !lastSentImage.value) {
    ElMessage.warning('没有可重试的消息')
    return
  }
  // 移除 AI 错误消息
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg && lastMsg.error) {
    const idx = agentStore.messages.lastIndexOf(lastMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  // 移除最后一条用户消息（避免重复）
  const lastUserMsg = [...agentStore.messages].reverse().find(m => m.role === 'user')
  if (lastUserMsg) {
    const idx = agentStore.messages.lastIndexOf(lastUserMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  handleSend({ text: lastSentMessage.value, files: lastSentImage.value ? [lastSentImage.value] : [] })
}

// ── 停止 ──
function handleStop() {
  agentStore.abort()
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg) {
    lastMsg.loading = false
    lastMsg.thinking = false
    if (lastMsg.toolCalls) {
      lastMsg.toolCalls.forEach((tc) => {
        if (tc.status === 'running') tc.status = 'failed'
      })
    }
    lastMsg.content += '\n[已停止生成]'
  }
}

// ── 滚动 ──
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// ── 快捷检测 ──
async function handleQuickDetect(type) {
  if (type === 'single') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      agentStore.addMessage({
        role: 'user',
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      })
      agentStore.addMessage({
        role: 'assistant',
        content: '正在检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      try {
        const result = await detectSingle(formData)
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `检测完成！发现 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
          lastMsg.loading = false
          lastMsg.detectionResult = result
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = '检测失败，请重试'
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  } else if (type === 'batch') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,.zip'
    input.multiple = true
    input.onchange = async (e) => {
      const files = Array.from(e.target.files)
      if (!files.length) return
      const isZip = files.some((f) => f.name.endsWith('.zip'))
      const formData = new FormData()
      if (isZip && files.length === 1) {
        formData.append('file', files[0])
        agentStore.addMessage({ role: 'user', content: `[快捷检测] ZIP: ${files[0].name}` })
      } else {
        files.forEach((f) => formData.append('files', f))
        agentStore.addMessage({
          role: 'user',
          content: `[快捷检测] ${files.length} 张图片`,
          images: files.map((f) => URL.createObjectURL(f)),
        })
      }
      agentStore.addMessage({
        role: 'assistant',
        content: '正在批量检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData)
        const result = await apiCall
        const lastMsg = agentStore.getLastAssistantMessage()
        if (!lastMsg) return
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`
          lastMsg.loading = false
          lastMsg.error = true
          return
        }
        lastMsg.content = `批量检测完成！共 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
        lastMsg.loading = false
        lastMsg.detectionResult = result
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `批量检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  }
}

async function handleVideoDetect() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,video/avi,video/quicktime,video/x-msvideo'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      ElMessage.warning('视频文件不能超过 50MB')
      return
    }
    const videoUrl = URL.createObjectURL(file)
    agentStore.addMessage({
      role: 'user',
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    })
    agentStore.addMessage({
      role: 'assistant',
      content: '正在上传视频...',
      loading: true,
      toolCalls: [],
    })
    agentStore.setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const uploadResult = await detectVideo(formData)
      const taskId = uploadResult.task_id
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) lastMsg.content = '视频已上传，正在处理中...'
      await pollVideoProgress(taskId)
    } catch (err) {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `视频检测失败：${err.message || err}`
        lastMsg.loading = false
        lastMsg.error = true
      }
    } finally {
      agentStore.setLoading(false)
    }
  }
  input.click()
}

async function pollVideoProgress(taskId) {
  const pollInterval = 3000
  return new Promise((resolve) => {
    const poll = async () => {
      try {
        const result = await getVideoStatus(taskId)
        if (result.status === 'completed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测完成！发现 ${result.total_objects || 0} 个目标。`
            lastMsg.loading = false
            lastMsg.detectionResult = result
          }
          resolve(result)
        } else if (result.status === 'failed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测失败：${result.error_message || '未知错误'}`
            lastMsg.loading = false
            lastMsg.error = true
          }
          resolve(null)
        } else {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) lastMsg.content = `视频检测中... ${result.progress || 0}%`
          setTimeout(poll, pollInterval)
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `视频检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
        resolve(null)
      }
    }
    setTimeout(poll, pollInterval)
  })
}

onMounted(async () => {
  await agentStore.fetchSessions()
  if (agentStore.messages.length === 0) {
    // 欢迎消息在模板中通过 v-if 处理
  }
})
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: 100%;
  background: #f5f6f7;
  overflow: hidden;
}

/* ── 主对话区域 ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f6f7;
}

/* ── 顶部栏 ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
}

/* ── 欢迎区域 ── */
.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.welcome-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.welcome-area h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.welcome-desc {
  font-size: 14px;
  color: #909399;
  margin: 0 0 32px;
}

.welcome-tips {
  display: flex;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #409eff;
    color: #409eff;
    background: #ecf5ff;
  }
}

/* ── 消息项 ── */
.message-item {
  margin-bottom: 20px;
}

.message-wrapper {
  display: flex;
  max-width: 75%;
}

.message-user-wrapper {
  margin-left: auto;
  justify-content: flex-end;
}

.message-assistant-wrapper {
  margin-right: auto;
  justify-content: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.message-content {
  white-space: pre-wrap;
}

.streaming-text {
  &::after {
    content: '|';
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  :deep(th), :deep(td) {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  :deep(code) {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

/* ── 附件 ── */
.message-attachment {
  margin-top: 8px;
  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;
  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

/* ── 思考中 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  span {
    width: 8px;
    height: 8px;
    background: #409eff;
    border-radius: 50%;
    animation: thinkingPulse 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes thinkingPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1.2); }
}

.thinking-text {
  font-size: 13px;
  color: #909399;
  font-style: italic;
}

/* ── 打字中 ── */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

/* ── 工具调用时间线 ── */
.tool-timeline {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.tool-timeline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  &:not(:last-child) {
    border-bottom: 1px dashed #e8e8e8;
  }
}

.tool-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #409eff;
  font-size: 13px;
}

.tool-completed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #67c23a;
  font-size: 13px;
}

.tool-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.tool-result-detail {
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

/* ── 错误重试 ── */
.error-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
```
**当前版本（缺失/被改）**：
```vue
<template>
  <div class="chat-page">
    <!-- ── 左侧会话列表 ── -->
    <ChatSidebar
      :sessions="agentStore.sessions"
      :current-session-id="agentStore.currentSessionId"
      @new-chat="handleNewSession"
      @switch-session="handleSwitchSession"
      @delete-session="handleDeleteSession"
      @rename-session="handleRenameSession"
    />

    <!-- ── 主对话区域 ── -->
    <div class="chat-main">
      <!-- 顶部栏：当前会话标题 + 操作 -->
      <div class="chat-header">
        <div class="header-left">
          <span class="header-title">{{ currentSessionTitle }}</span>
        </div>
        <div class="header-actions">
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('single')"
          >
            📷 单图检测
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleQuickDetect('batch')"
          >
            📁 批量/ZIP
          </el-button>
          <el-button
            size="small"
            :disabled="agentStore.isLoading"
            @click="handleVideoDetect"
          >
            🎬 视频
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <!-- 欢迎消息（无会话时） -->
        <div v-if="agentStore.messages.length === 0" class="welcome-area">
          <div class="welcome-icon">
            <el-icon :size="56"><ChatDotRound /></el-icon>
          </div>
          <h2>你好！我是火灾烟雾智能检测智能体</h2>
          <p class="welcome-desc">上传图片或视频，我可以帮你检测火情和烟雾目标</p>
          <div class="welcome-tips">
            <div class="tip-item" @click="inputTextPlaceholder = '检测一下这张图片中的火情'">
              <el-icon><Picture /></el-icon>
              <span>图片检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '帮我分析这段视频中的烟雾'">
              <el-icon><VideoCamera /></el-icon>
              <span>视频检测</span>
            </div>
            <div class="tip-item" @click="inputTextPlaceholder = '批量检测这个 ZIP 中的图片'">
              <el-icon><Folder /></el-icon>
              <span>批量检测</span>
            </div>
          </div>
        </div>

        <!-- 消息项 -->
        <div
          v-for="(msg, index) in agentStore.messages"
          :key="index"
          :class="['message-item', `message-${msg.role}`]"
        >
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message-wrapper message-user-wrapper">
            <div class="message-bubble user-bubble">
              <div v-if="msg.content" class="message-content">{{ msg.content }}</div>
              <!-- 单张图片附件 -->
              <div v-if="msg.imagePreview" class="message-attachment">
                <img :src="msg.imagePreview" alt="附件图片" />
              </div>
              <!-- 多图附件 -->
              <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
                <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
              </div>
            </div>
          </div>

          <!-- AI 消息 -->
          <div v-else-if="msg.role === 'assistant'" class="message-wrapper message-assistant-wrapper">
            <div class="message-bubble assistant-bubble">
              <!-- 思考中动画 -->
              <div v-if="msg.thinking" class="thinking-indicator">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
                <span class="thinking-text">{{ msg.thinkingContent || '正在思考中...' }}</span>
              </div>

              <!-- 打字中动画 -->
              <div v-else-if="msg.loading && !msg.thinking" class="typing-indicator">
                <span></span><span></span><span></span>
              </div>

              <!-- Markdown 渲染 -->
              <div
                v-if="!msg.loading && msg.content && !msg.thinking"
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <!-- 流式文本 -->
              <div
                v-if="msg.loading && msg.content && !msg.thinking"
                class="message-content streaming-text"
              >{{ msg.content }}</div>

              <!-- 工具调用时间线 -->
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-timeline">
                <div
                  v-for="(tc, tIdx) in msg.toolCalls"
                  :key="tIdx"
                  :class="['tool-timeline-item', `tool-status-${tc.status}`]"
                >
                  <div v-if="tc.status === 'running'" class="tool-loading">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>正在调用工具：{{ tc.tool }}</span>
                  </div>
                  <div v-else-if="tc.status === 'completed'" class="tool-completed">
                    <el-icon color="#67c23a"><CircleCheck /></el-icon>
                    <span>工具 {{ tc.tool }} 执行完成</span>
                    <el-popover
                      v-if="tc.resultSummary"
                      placement="right"
                      :width="300"
                      trigger="click"
                    >
                      <template #reference>
                        <el-button text size="small" type="primary">查看详情</el-button>
                      </template>
                      <div class="tool-result-detail">{{ tc.resultSummary }}</div>
                    </el-popover>
                  </div>
                  <div v-else-if="tc.status === 'failed'" class="tool-failed">
                    <el-icon color="#f56c6c"><CircleClose /></el-icon>
                    <span>工具 {{ tc.tool }} 调用失败</span>
                  </div>
                </div>
              </div>

              <!-- 错误 + 重试 -->
              <div v-if="msg.error" class="error-actions">
                <el-button type="warning" size="small" @click="retryLastMessage">
                  <el-icon><Refresh /></el-icon> 重试
                </el-button>
              </div>

              <!-- 检测结果卡片 -->
              <DetectionResultCard
                v-if="msg.detectionResult"
                :result="msg.detectionResult"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <ChatInput
        :disabled="agentStore.isLoading"
        @send="handleSend"
        @stop="handleStop"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 豆包风格全屏聊天界面
 *
 * 功能：
 *   - 左侧会话列表（可折叠）
 *   - 消息气泡（用户/AI 区分，Markdown 渲染）
 *   - 完整 SSE 事件协议（thinking/tool_start/tool_end/text_chunk/done/error）
 *   - 检测结果卡片 + 工具调用时间线
 *   - 快捷操作（单图/批量/视频检测）
 *   - 拖拽文件 + 文字输入 + 发送
 *   - 重试、停止生成
 */
import ChatInput from '@/components/chat/ChatInput.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import DetectionResultCard from '@/components/DetectionResultCard.vue'
import { useAgentStore } from '@/stores/agent'
import request from '@/utils/request'
import { renderMarkdown } from '@/utils/markdown'
import { streamChat } from '@/utils/stream'
import { detectBatch, detectSingle, detectVideo, detectZip, getVideoStatus } from '@/api/detection'
import { ChatDotRound, CircleCheck, CircleClose, Folder, Loading, Picture, Refresh, VideoCamera } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref } from 'vue'

// ── Store ──
const agentStore = useAgentStore()

// ── 响应式状态 ──
const messageListRef = ref(null)
const inputTextPlaceholder = ref('')

// 重试用
const lastSentMessage = ref('')
const lastSentImage = ref(null)
const lastSentFiles = ref([])

// ── 计算属性 ──
const currentSessionTitle = computed(() => {
  if (!agentStore.currentSessionId) return '新对话'
  const session = agentStore.sessions.find((s) => s.id === agentStore.currentSessionId)
  return session?.title || '新对话'
})

// ── 会话管理 ──
function handleNewSession() {
  agentStore.newChat()
}

async function handleSwitchSession(sessionId) {
  await agentStore.switchSession(sessionId)
  scrollToBottom()
}

async function handleDeleteSession(sessionId) {
  await agentStore.deleteSession(sessionId)
}

async function handleRenameSession(sessionId, title) {
  try {
    await agentStore.renameSession(sessionId, title)
    ElMessage.success('重命名成功')
  } catch (err) {
    ElMessage.error('重命名失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
  }
}

// ── 发送消息 ──
async function handleSend({ text, files }) {
  if (!text && (!files || files.length === 0)) return

  const message = text || ''
  let uploadedFiles = []

  // Step 1: 如果有文件，先上传到后端
  if (files && files.length > 0) {
    ElMessage.info(`正在上传 ${files.length} 个文件...`)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const res = await request.post('/chat/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        uploadedFiles.push(res.data) // {url, type, name}
      }
      ElMessage.success(`文件上传完成 (${uploadedFiles.length} 个)`)
    } catch (err) {
      ElMessage.error('文件上传失败: ' + (err.response?.data?.detail || err.message || '未知错误'))
      return
    }
  }

  // Step 2: 添加用户消息（含文件预览）
  lastSentMessage.value = message
  lastSentImage.value = (files && files.length > 0) ? files[0] : null
  lastSentFiles.value = uploadedFiles

  const userMsg = {
    role: 'user',
    content: message,
  }

  if (files && files.length > 0) {
    const imageFiles = files.filter(f => f.type?.startsWith('image/'))
    // 单张图片预览
    if (imageFiles.length === 1) {
      userMsg.image = imageFiles[0].name
      userMsg.imagePreview = URL.createObjectURL(imageFiles[0])
    }
    // 多图预览
    else if (imageFiles.length > 1) {
      userMsg.images = imageFiles.map(f => URL.createObjectURL(f))
    }
    // 如果只有非图片文件且没有文字，用文件名填充消息内容
    if (imageFiles.length < files.length && !message) {
      const fileNames = files.map(f => f.name).join(', ')
      userMsg.content = `[文件] ${fileNames}`
    }
  }

  agentStore.addMessage(userMsg)

  // Step 3: 添加 AI 加载占位
  agentStore.addMessage({
    role: 'assistant',
    content: '',
    loading: true,
    toolCalls: [],
  })

  agentStore.setLoading(true)
  scrollToBottom()

  // Step 4: 构造请求体并发起 SSE
  const requestBody = { content: message }
  if (uploadedFiles.length > 0) {
    requestBody.files = uploadedFiles
  }
  if (agentStore.currentSessionId) {
    requestBody.session_id = agentStore.currentSessionId
  }

  let fullContent = ''

  const stop = streamChat('/api/chat/messages/stream', requestBody, {
    onMessage: (data) => {
      console.log('[SSE事件]', data.type, data)
      const lastMsg = agentStore.getLastAssistantMessage()
      if (!lastMsg) return

      switch (data.type) {
        case 'thinking':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          lastMsg.thinking = true
          lastMsg.thinkingContent = data.content || '正在分析问题...'
          lastMsg.loading = true
          break

        case 'tool_start': {
          lastMsg.thinking = false
          lastMsg.loading = true
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool || '未知工具',
            input: data.input,
            status: 'running',
            startTime: Date.now(),
          })
          break
        }

        case 'tool_end': {
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
              try {
                const result = JSON.parse(data.result)
                if (result.detections) {
                  runningTc.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
                  lastMsg.detectionResult = result
                  lastMsg.loading = false
                } else {
                  runningTc.resultSummary = JSON.stringify(result).substring(0, 200)
                }
              } catch {
                runningTc.resultSummary = (data.result || '').substring(0, 200)
              }
            }
          }
          lastMsg.toolCall = { tool: data.tool, result: data.result }
          break
        }

        case 'text_chunk':
          lastMsg.thinking = false
          lastMsg.loading = true
          fullContent += data.content || ''
          lastMsg.content = fullContent
          break

        case 'done':
          if (data.session_id && !agentStore.currentSessionId) {
            agentStore.currentSessionId = data.session_id
          }
          if (data.response && !fullContent) {
            lastMsg.content = data.response
          }
          lastMsg.loading = false
          lastMsg.thinking = false
          agentStore.setLoading(false)
          agentStore.fetchSessions()
          break

        case 'error':
          lastMsg.content = data.content || '处理请求时发生错误'
          lastMsg.loading = false
          lastMsg.thinking = false
          lastMsg.error = true
          agentStore.setLoading(false)
          break

        case 'tool_call':
          lastMsg.thinking = false
          lastMsg.loading = true
          lastMsg.toolCall = { tool: data.tool, input: data.input }
          if (!lastMsg.toolCalls) lastMsg.toolCalls = []
          lastMsg.toolCalls.push({
            tool: data.tool,
            input: data.input,
            status: 'running',
            startTime: Date.now(),
          })
          break

        case 'tool_result':
          if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
            const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
            if (runningTc) {
              runningTc.status = 'completed'
              runningTc.result = data.result
            }
          }
          try {
            const result = JSON.parse(data.result)
            if (result.detections) {
              lastMsg.detectionResult = result
              lastMsg.loading = false
            }
          } catch (e) {
            lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`
          }
          break

        default:
          if (data.content) {
            lastMsg.thinking = false
            lastMsg.loading = true
            fullContent += data.content
            lastMsg.content = fullContent
          }
          break
      }

      scrollToBottom()
    },

    onDone: () => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        if (lastMsg.loading && !lastMsg.content && !lastMsg.detectionResult) {
          lastMsg.content = '处理完成。'
        }
        lastMsg.loading = false
        lastMsg.thinking = false
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      scrollToBottom()
    },

    onError: (err) => {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `抱歉，处理出错了：${err.message}`
        lastMsg.loading = false
        lastMsg.thinking = false
        lastMsg.error = true
      }
      agentStore.setLoading(false)
      agentStore.abortController = null
      ElMessage.error('对话请求失败，请重试')
    },
  })

  agentStore.abortController = stop
}

// ── 重试 ──
async function retryLastMessage() {
  if (!lastSentMessage.value && !lastSentImage.value) {
    ElMessage.warning('没有可重试的消息')
    return
  }
  // 移除 AI 错误消息
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg && lastMsg.error) {
    const idx = agentStore.messages.lastIndexOf(lastMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  // 移除最后一条用户消息（避免重复）
  const lastUserMsg = [...agentStore.messages].reverse().find(m => m.role === 'user')
  if (lastUserMsg) {
    const idx = agentStore.messages.lastIndexOf(lastUserMsg)
    if (idx >= 0) agentStore.messages.splice(idx, 1)
  }
  handleSend({ text: lastSentMessage.value, files: lastSentImage.value ? [lastSentImage.value] : [] })
}

// ── 停止 ──
function handleStop() {
  agentStore.abort()
  const lastMsg = agentStore.getLastAssistantMessage()
  if (lastMsg) {
    lastMsg.loading = false
    lastMsg.thinking = false
    if (lastMsg.toolCalls) {
      lastMsg.toolCalls.forEach((tc) => {
        if (tc.status === 'running') tc.status = 'failed'
      })
    }
    lastMsg.content += '\n[已停止生成]'
  }
}

// ── 滚动 ──
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// ── 快捷检测 ──
async function handleQuickDetect(type) {
  if (type === 'single') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      agentStore.addMessage({
        role: 'user',
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      })
      agentStore.addMessage({
        role: 'assistant',
        content: '正在检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      try {
        const result = await detectSingle(formData)
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `检测完成！发现 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
          lastMsg.loading = false
          lastMsg.detectionResult = result
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = '检测失败，请重试'
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  } else if (type === 'batch') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,.zip'
    input.multiple = true
    input.onchange = async (e) => {
      const files = Array.from(e.target.files)
      if (!files.length) return
      const isZip = files.some((f) => f.name.endsWith('.zip'))
      const formData = new FormData()
      if (isZip && files.length === 1) {
        formData.append('file', files[0])
        agentStore.addMessage({ role: 'user', content: `[快捷检测] ZIP: ${files[0].name}` })
      } else {
        files.forEach((f) => formData.append('files', f))
        agentStore.addMessage({
          role: 'user',
          content: `[快捷检测] ${files.length} 张图片`,
          images: files.map((f) => URL.createObjectURL(f)),
        })
      }
      agentStore.addMessage({
        role: 'assistant',
        content: '正在批量检测中...',
        loading: true,
        toolCalls: [],
      })
      agentStore.setLoading(true)
      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData)
        const result = await apiCall
        const lastMsg = agentStore.getLastAssistantMessage()
        if (!lastMsg) return
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`
          lastMsg.loading = false
          lastMsg.error = true
          return
        }
        lastMsg.content = `批量检测完成！共 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标。`
        lastMsg.loading = false
        lastMsg.detectionResult = result
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `批量检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
      } finally {
        agentStore.setLoading(false)
      }
    }
    input.click()
  }
}

async function handleVideoDetect() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'video/mp4,video/avi,video/quicktime,video/x-msvideo'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      ElMessage.warning('视频文件不能超过 50MB')
      return
    }
    const videoUrl = URL.createObjectURL(file)
    agentStore.addMessage({
      role: 'user',
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    })
    agentStore.addMessage({
      role: 'assistant',
      content: '正在上传视频...',
      loading: true,
      toolCalls: [],
    })
    agentStore.setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const uploadResult = await detectVideo(formData)
      const taskId = uploadResult.task_id
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) lastMsg.content = '视频已上传，正在处理中...'
      await pollVideoProgress(taskId)
    } catch (err) {
      const lastMsg = agentStore.getLastAssistantMessage()
      if (lastMsg) {
        lastMsg.content = `视频检测失败：${err.message || err}`
        lastMsg.loading = false
        lastMsg.error = true
      }
    } finally {
      agentStore.setLoading(false)
    }
  }
  input.click()
}

async function pollVideoProgress(taskId) {
  const pollInterval = 3000
  return new Promise((resolve) => {
    const poll = async () => {
      try {
        const result = await getVideoStatus(taskId)
        if (result.status === 'completed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测完成！发现 ${result.total_objects || 0} 个目标。`
            lastMsg.loading = false
            lastMsg.detectionResult = result
          }
          resolve(result)
        } else if (result.status === 'failed') {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) {
            lastMsg.content = `视频检测失败：${result.error_message || '未知错误'}`
            lastMsg.loading = false
            lastMsg.error = true
          }
          resolve(null)
        } else {
          const lastMsg = agentStore.getLastAssistantMessage()
          if (lastMsg) lastMsg.content = `视频检测中... ${result.progress || 0}%`
          setTimeout(poll, pollInterval)
        }
      } catch (err) {
        const lastMsg = agentStore.getLastAssistantMessage()
        if (lastMsg) {
          lastMsg.content = `视频检测失败：${err.message || err}`
          lastMsg.loading = false
          lastMsg.error = true
        }
        resolve(null)
      }
    }
    setTimeout(poll, pollInterval)
  })
}

onMounted(async () => {
  await agentStore.fetchSessions()
  if (agentStore.messages.length === 0) {
    // 欢迎消息在模板中通过 v-if 处理
  }
})
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: 100%;
  background: #f5f6f7;
  overflow: hidden;
}

/* ── 主对话区域 ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f6f7;
}

/* ── 顶部栏 ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
}

/* ── 欢迎区域 ── */
.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.welcome-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.welcome-area h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px;
}

.welcome-desc {
  font-size: 14px;
  color: #909399;
  margin: 0 0 32px;
}

.welcome-tips {
  display: flex;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #409eff;
    color: #409eff;
    background: #ecf5ff;
  }
}

/* ── 消息项 ── */
.message-item {
  margin-bottom: 20px;
}

.message-wrapper {
  display: flex;
  max-width: 75%;
}

.message-user-wrapper {
  margin-left: auto;
  justify-content: flex-end;
}

.message-assistant-wrapper {
  margin-right: auto;
  justify-content: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.message-content {
  white-space: pre-wrap;
}

.streaming-text {
  &::after {
    content: '|';
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.markdown-body {
  :deep(h1), :deep(h2), :deep(h3) {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  :deep(th), :deep(td) {
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  :deep(code) {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

/* ── 附件 ── */
.message-attachment {
  margin-top: 8px;
  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;
  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }
}

/* ── 思考中 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  span {
    width: 8px;
    height: 8px;
    background: #409eff;
    border-radius: 50%;
    animation: thinkingPulse 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes thinkingPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1.2); }
}

.thinking-text {
  font-size: 13px;
  color: #909399;
  font-style: italic;
}

/* ── 打字中 ── */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
  span {
    width: 6px;
    height: 6px;
    background: #999;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }
  span:nth-child(2) { animation-delay: 0.2s; }
  span:nth-child(3) { animation-delay: 0.4s; }
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

/* ── 工具调用时间线 ── */
.tool-timeline {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.tool-timeline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  &:not(:last-child) {
    border-bottom: 1px dashed #e8e8e8;
  }
}

.tool-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #409eff;
  font-size: 13px;
}

.tool-completed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #67c23a;
  font-size: 13px;
}

.tool-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 13px;
}

.tool-result-detail {
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

/* ── 错误重试 ── */
.error-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
```
**统一差异（unified diff）**：
```diff
--- backup/frontend/src/views/ChatPage.vue
+++ current/frontend/src/views/ChatPage.vue
@@ -324,6 +324,7 @@
 
   const stop = streamChat('/api/chat/messages/stream', requestBody, {
     onMessage: (data) => {
+      console.log('[SSE事件]', data.type, data)
       const lastMsg = agentStore.getLastAssistantMessage()
       if (!lastMsg) return
 
@@ -343,7 +344,7 @@
           if (!lastMsg.toolCalls) lastMsg.toolCalls = []
           lastMsg.toolCalls.push({
             tool: data.tool || '未知工具',
-            input: data.input || data.args,
+            input: data.input,
             status: 'running',
             startTime: Date.now(),
           })
@@ -357,27 +358,16 @@
               runningTc.status = 'completed'
               runningTc.result = data.result
               try {
-                const result = data.result ? JSON.parse(data.result) : {}
-                if (result.error) {
-                  runningTc.status = 'failed'
-                  runningTc.resultSummary = result.error
-                  const errorText = `检测失败：${result.error}`
-                  lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
-                  lastMsg.loading = false
-                } else if (Array.isArray(result.detections)) {
+                const result = JSON.parse(data.result)
+                if (result.detections) {
                   runningTc.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
                   lastMsg.detectionResult = result
                   lastMsg.loading = false
                 } else {
                   runningTc.resultSummary = JSON.stringify(result).substring(0, 200)
                 }
-              } catch (parseErr) {
-                runningTc.status = 'failed'
+              } catch {
                 runningTc.resultSummary = (data.result || '').substring(0, 200)
-                const failText = '工具结果解析失败，请稍后重试'
-                lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${failText}` : failText
-                lastMsg.loading = false
-                console.error('[tool_end] 解析失败:', parseErr, data.result)
               }
             }
           }
@@ -416,52 +406,34 @@
         case 'tool_call':
           lastMsg.thinking = false
           lastMsg.loading = true
-          lastMsg.toolCall = { tool: data.tool, input: data.input || data.args }
+          lastMsg.toolCall = { tool: data.tool, input: data.input }
           if (!lastMsg.toolCalls) lastMsg.toolCalls = []
           lastMsg.toolCalls.push({
             tool: data.tool,
-            input: data.input || data.args,
+            input: data.input,
             status: 'running',
             startTime: Date.now(),
           })
           break
 
-        case 'tool_result': {
-          let toolResult = null
+        case 'tool_result':
           if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
             const runningTc = [...lastMsg.toolCalls].reverse().find((tc) => tc.status === 'running')
             if (runningTc) {
               runningTc.status = 'completed'
               runningTc.result = data.result
-              toolResult = runningTc
             }
           }
           try {
-            const result = data.result ? JSON.parse(data.result) : {}
-            if (result.error) {
-              if (toolResult) toolResult.status = 'failed'
-              const errorText = `检测失败：${result.error}`
-              lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${errorText}` : errorText
-              lastMsg.loading = false
-            } else if (Array.isArray(result.detections)) {
-              if (toolResult) {
-                toolResult.resultSummary = `检测到 ${(result.fire_object_count || 0) + (result.smoke_object_count || 0)} 个目标`
-              }
+            const result = JSON.parse(data.result)
+            if (result.detections) {
               lastMsg.detectionResult = result
               lastMsg.loading = false
-            } else if (toolResult) {
-              toolResult.resultSummary = JSON.stringify(result).substring(0, 200)
             }
-          } catch (parseErr) {
-            if (toolResult) toolResult.status = 'failed'
-            if (toolResult) toolResult.resultSummary = (data.result || '').substring(0, 200)
-            const failText = '工具结果解析失败，请稍后重试'
-            lastMsg.content = lastMsg.content ? `${lastMsg.content}\n${failText}` : failText
-            lastMsg.loading = false
-            console.error('[tool_result] 解析失败:', parseErr, data.result)
+          } catch (e) {
+            lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`
           }
           break
-        }
 
         default:
           if (data.content) {
```
**结论**：恢复对 result.error、空 detections、解析失败的容错处理，确保标注图正常渲染。


---

### 文件：backend/app/agent/detection_agent.py
**优先级**：P1
**影响说明**：Agent 编排与工具调用逻辑变化，影响 ReAct 循环、工具输出截断、SSE 事件封装。
**备份版本（原功能）**：
```python
"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  - 创建 LangChain ReAct Agent（create_openai_tools_agent）
  - 绑定 rsod_agent 模块化工具（detection / knowledge / stats / user）
  - 提供 chat() 同步调用 和 chat_stream() 流式调用

使用方式：
  from app.agent.detection_agent import detection_agent
  result = await detection_agent.chat("检测这张图片", history=[...])
"""
from typing import AsyncGenerator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.agent.prompts import DETECTION_AGENT_SYSTEM_PROMPT
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 导入工具（在 try/except 外层，若导入失败则不绑定）
try:
    from app.agent.tools.detection_tool import (
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
    )
    from app.agent.tools.knowledge_tool import search_knowledge
    from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
    from app.agent.tools.user_tool import query_user_list

    DETECTION_TOOLS = [
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
        search_knowledge,
        query_detection_stats,
        query_detection_history,
        query_user_list,
    ]
except Exception as _tools_import_err:
    logger.error("检测工具导入失败，Agent 将以无工具模式运行: %s", _tools_import_err)
    DETECTION_TOOLS = []


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        self.available: bool = False
        self.executor: Optional[AgentExecutor] = None

        try:
            # 根据配置选择 LLM 后端
            if settings.LLM_STUB_MODE:
                logger.info("DetectionAgent 在 stub 模式下启动，跳过 LLM 初始化")
                self.available = False
                return

            if settings.USE_LOCAL_LLM:
                self.llm = ChatOpenAI(
                    model=settings.OLLAMA_MODEL,
                    api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )
            else:
                self.llm = ChatOpenAI(
                    model=settings.QWEN_MODEL,
                    api_key=settings.QWEN_API_KEY,
                    base_url=settings.QWEN_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", DETECTION_AGENT_SYSTEM_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )

            agent = create_openai_tools_agent(self.llm, DETECTION_TOOLS, prompt)

            self.executor = AgentExecutor(
                agent=agent,
                tools=DETECTION_TOOLS,
                max_iterations=5,
                return_intermediate_steps=True,
                verbose=False,
            )
            self.available = True
            logger.info(
                "DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS)
            )
        except Exception as e:
            logger.error("DetectionAgent 初始化失败，将以降级模式运行: %s", e)
            self.available = False
            self.executor = None

    def _build_chat_history(self, history: list) -> list:
        """将 DB 中的历史消息转为 LangChain Message 对象"""
        chat_history = []
        if not history:
            return chat_history
        for msg in history[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        return chat_history

    async def chat(self, message: str, history: list = None) -> dict:
        """
        异步调用 Agent，返回完整结果。

        Args:
            message: 用户文本消息
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"output": "...", "intermediate_steps": [...]}
        """
        if not self.available:
            raise RuntimeError("Agent 不可用，请降级为纯 LLM 调用")

        chat_history = self._build_chat_history(history)

        try:
            result = await self.executor.ainvoke(
                {"input": message, "chat_history": chat_history}
            )
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", e, exc_info=True)
            raise

    async def chat_stream(
        self, message: str, history: list = None
    ) -> AsyncGenerator:
        """
        流式调用 Agent，yield SSE 事件字典。

        Yields:
            {"type": "text_chunk", "content": "..."}   — LLM 生成的文本片段
            {"type": "tool_call", "tool": "...", "input": {...}}  — 开始调用工具
            {"type": "tool_result", "tool": "...", "result": "..."}  — 工具返回
            {"type": "error", "content": "..."}         — 出错
        """
        if not self.available:
            yield {"type": "error", "content": "Agent 不可用"}
            return

        chat_history = self._build_chat_history(history)

        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield {"type": "text_chunk", "content": chunk.content}

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("Agent 工具调用: %s, input=%s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info("Agent 工具完成: %s", tool_name)
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", e, exc_info=True)
            yield {"type": "error", "content": f"Agent 执行出错：{str(e)}"}


# 全局单例
detection_agent = DetectionAgent()
```
**当前版本（缺失/被改）**：
```python
"""
检测智能体 — ReAct Agent + 检测工具绑定

职责：
  - 创建 LangChain ReAct Agent（create_openai_tools_agent）
  - 绑定 rsod_agent 模块化工具（detection / knowledge / stats / user）
  - 提供 chat() 同步调用 和 chat_stream() 流式调用

使用方式：
  from app.agent.detection_agent import detection_agent
  result = await detection_agent.chat("检测这张图片", history=[...])
"""
from typing import AsyncGenerator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.agent.prompts import DETECTION_AGENT_SYSTEM_PROMPT
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 导入工具（在 try/except 外层，若导入失败则不绑定）
try:
    from app.agent.tools.detection_tool import (
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
    )
    from app.agent.tools.knowledge_tool import search_knowledge
    from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
    from app.agent.tools.user_tool import query_user_list

    DETECTION_TOOLS = [
        detect_single_image,
        detect_batch_images,
        detect_zip_images_file,
        detect_video_file,
        search_knowledge,
        query_detection_stats,
        query_detection_history,
        query_user_list,
    ]
except Exception as _tools_import_err:
    logger.error("检测工具导入失败，Agent 将以无工具模式运行: %s", _tools_import_err)
    DETECTION_TOOLS = []


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 创建和对话逻辑"""

    def __init__(self):
        self.available: bool = False
        self.executor: Optional[AgentExecutor] = None

        try:
            # 根据配置选择 LLM 后端
            if settings.LLM_STUB_MODE:
                logger.info("DetectionAgent 在 stub 模式下启动，跳过 LLM 初始化")
                self.available = False
                return

            if settings.USE_LOCAL_LLM:
                self.llm = ChatOpenAI(
                    model=settings.OLLAMA_MODEL,
                    api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )
            else:
                self.llm = ChatOpenAI(
                    model=settings.QWEN_MODEL,
                    api_key=settings.QWEN_API_KEY,
                    base_url=settings.QWEN_BASE_URL,
                    temperature=0.1,
                    max_tokens=2000,
                )

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", DETECTION_AGENT_SYSTEM_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )

            agent = create_openai_tools_agent(self.llm, DETECTION_TOOLS, prompt)

            self.executor = AgentExecutor(
                agent=agent,
                tools=DETECTION_TOOLS,
                max_iterations=5,
                return_intermediate_steps=True,
                verbose=False,
            )
            self.available = True
            logger.info(
                "DetectionAgent 初始化完成，绑定 %d 个工具", len(DETECTION_TOOLS)
            )
        except Exception as e:
            logger.error("DetectionAgent 初始化失败，将以降级模式运行: %s", e)
            self.available = False
            self.executor = None

    def _build_chat_history(self, history: list) -> list:
        """将 DB 中的历史消息转为 LangChain Message 对象"""
        chat_history = []
        if not history:
            return chat_history
        for msg in history[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        return chat_history

    async def chat(self, message: str, history: list = None) -> dict:
        """
        异步调用 Agent，返回完整结果。

        Args:
            message: 用户文本消息
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"output": "...", "intermediate_steps": [...]}
        """
        if not self.available:
            raise RuntimeError("Agent 不可用，请降级为纯 LLM 调用")

        chat_history = self._build_chat_history(history)

        try:
            result = await self.executor.ainvoke(
                {"input": message, "chat_history": chat_history}
            )
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", e, exc_info=True)
            raise

    async def chat_stream(
        self, message: str, history: list = None
    ) -> AsyncGenerator:
        """
        流式调用 Agent，yield SSE 事件字典。

        Yields:
            {"type": "text_chunk", "content": "..."}   — LLM 生成的文本片段
            {"type": "tool_call", "tool": "...", "input": {...}}  — 开始调用工具
            {"type": "tool_result", "tool": "...", "result": "..."}  — 工具返回
            {"type": "error", "content": "..."}         — 出错
        """
        if not self.available:
            yield {"type": "error", "content": "Agent 不可用"}
            return

        chat_history = self._build_chat_history(history)

        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield {"type": "text_chunk", "content": chunk.content}

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("Agent 工具调用: %s, input=%s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "input": tool_input,
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info("Agent 工具完成: %s", tool_name)
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": str(tool_output)[:500] if tool_output else "",
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", e, exc_info=True)
            yield {"type": "error", "content": f"Agent 执行出错：{str(e)}"}


# 全局单例
detection_agent = DetectionAgent()
```
**统一差异（unified diff）**：
```diff
--- backup/backend/app/agent/detection_agent.py
+++ current/backend/app/agent/detection_agent.py
@@ -198,7 +198,7 @@
                     yield {
                         "type": "tool_result",
                         "tool": tool_name,
-                        "result": str(tool_output) if tool_output else "",
+                        "result": str(tool_output)[:500] if tool_output else "",
                     }
 
         except Exception as e:
```
**结论**：避免截断工具输出（特别是 base64 标注图），统一 SSE 事件字段。


---

### 文件：frontend/src/components/DetectionResultCard.vue
**优先级**：P1
**影响说明**：检测结果卡片组件变化，影响标注图 base64 兜底展示与检测结果渲染。
**备份版本（原功能）**：
```vue
<template>
  <div v-if="isValidResult" class="detection-result-card">
    <div class="card-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>检测结果</span>
      <el-tag size="small" type="success">
        {{ totalObjects }} 个目标
      </el-tag>
    </div>

    <div class="card-body">
      <!-- 单图模式：标注图 -->
      <div class="result-image" v-if="annotatedImageSrc && !isBatch">
        <img
          :src="annotatedImageSrc"
          alt="检测标注图"
          @click="showFullImage = true"
        />
      </div>

      <!-- 单图模式：无可用标注图占位 -->
      <div class="result-image-placeholder" v-else-if="!isBatch && result.type !== 'video'">
        <el-icon><Picture /></el-icon>
        <span>标注图暂不可用</span>
      </div>

      <!-- 批量模式：多图展示 -->
      <div class="result-images-grid" v-if="isBatch && batchImages.length > 0">
        <div
          v-for="(img, index) in batchImages"
          :key="index"
          class="grid-image"
          @click="previewImage(img)"
        >
          <img :src="img.src" :alt="img.name" />
          <span class="image-name">{{ img.name }}</span>
        </div>
      </div>

      <!-- 视频检测结果：标注视频播放器 -->
      <div
        v-if="result.type === 'video'"
        class="video-result"
      >
        <div class="video-info">
          <el-tag type="info">时长: {{ result.duration_seconds }}s</el-tag>
          <el-tag type="info">FPS: {{ result.fps }}</el-tag>
          <el-tag type="info">采样帧: {{ result.processed_frames }}</el-tag>
          <el-tag type="success">目标: {{ totalObjects }}</el-tag>
        </div>
        <div v-if="result.annotated_video_url" class="video-player">
          <video
            :src="result.annotated_video_url"
            controls
            preload="metadata"
          ></video>
        </div>
        <div v-else-if="result.key_frames" class="frames-fallback">
          <p class="fallback-hint">标注视频生成中或上传失败，以下为关键帧预览：</p>
          <div class="frames-container">
            <div
              v-for="(frame, index) in thumbnailFrames"
              :key="index"
              class="frame-card"
              @click="previewVideoFrame(frame)"
            >
              <img
                :src="`data:image/jpeg;base64,${frame.annotated_image_base64}`"
                :alt="`帧 ${frame.frame_index}`"
              />
              <div class="frame-info">
                <span>{{ frame.timestamp }}s</span>
                <span>{{ frame.object_count }} 个目标</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">推理耗时</span>
          <span class="stat-value">{{ result.inference_time || result.total_inference_time || 0 }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">检测目标</span>
          <span class="stat-value">{{ totalObjects }} 个</span>
        </div>
        <div class="stat-item" v-if="isBatch">
          <span class="stat-label">图片数量</span>
          <span class="stat-value">{{ result.total_images ?? batchImages.length }} 张</span>
        </div>

        <!-- 类别统计表格 -->
        <el-table
          v-if="classCountsArray.length > 0"
          :data="classCountsArray"
          size="small"
          style="margin-top: 12px"
        >
          <el-table-column prop="className" label="类别" />
          <el-table-column prop="count" label="数量" width="80" />
        </el-table>
      </div>
    </div>

    <!-- 全屏图片预览 -->
    <el-dialog v-model="showFullImage" title="检测标注图" width="80%">
      <img
        v-if="previewSrc"
        :src="previewSrc"
        style="width: 100%"
        alt="检测标注图"
      />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * DetectionResultCard — 检测结果卡片组件
 *
 * 在对话消息中展示检测结果，包含：
 *   - 标注图预览（单图/批量多图，点击可放大）
 *   - 目标总数和推理耗时
 *   - 各类别数量统计表格
 */
import { DataAnalysis, Picture } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
});

const showFullImage = ref(false);
const previewSrc = ref(null);

/** 结果是否为合法对象 */
const isValidResult = computed(() => {
  return props.result && typeof props.result === 'object';
});

/** 判断是否为批量检测结果 */
const isBatch = computed(() => {
  return Array.isArray(props.result?.annotated_images) && props.result.annotated_images.length > 0;
});

/** 单图模式：标注图（优先使用 base64，避免 MinIO 预签名 URL 403） */
const annotatedImageSrc = computed(() => {
  if (!isValidResult.value) return null;
  if (props.result.annotated_image_base64) {
    return `data:image/jpeg;base64,${props.result.annotated_image_base64}`;
  }
  if (props.result.annotated_image_url) {
    return props.result.annotated_image_url;
  }
  return null;
});

/** 批量模式：标注图列表 */
const batchImages = computed(() => {
  if (!isBatch.value) return [];
  return props.result.annotated_images.map((img) => ({
    name: img.image_path || "image",
    src: `data:image/jpeg;base64,${img.annotated_image_base64}`,
  }));
});

/** 点击预览图片 */
function previewImage(img) {
  previewSrc.value = img.src;
  showFullImage.value = true;
}

/** 视频模式：缩略帧列表（限制显示数量） */
const thumbnailFrames = computed(() => {
  const frames = props.result.key_frames || [];
  return frames.slice(0, 6);
});

/** 点击预览视频帧 */
function previewVideoFrame(frame) {
  previewSrc.value = `data:image/jpeg;base64,${frame.annotated_image_base64}`;
  showFullImage.value = true;
}

/** 目标总数（兼容 total_objects 与 fire_object_count + smoke_object_count） */
const totalObjects = computed(() => {
  return props.result.total_objects
    ?? ((props.result.fire_object_count || 0) + (props.result.smoke_object_count || 0));
});

/** 类别统计转为数组（用于 el-table，兼容 data.class_counts） */
const classCountsArray = computed(() => {
  const counts = props.result.class_counts || props.result.data?.class_counts || {};
  return Object.entries(counts).map(([className, count]) => ({
    className,
    count,
  }));
});
</script>

<style lang="scss" scoped>
.detection-result-card {
  margin-top: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 600;
  font-size: 14px;
}

.card-body {
  display: flex;
  gap: 16px;
  padding: 12px;
}

.result-image {
  flex: 1;
  min-width: 0;

  img {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }
  }
}

.result-image-placeholder {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 160px;
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  color: #909399;
  font-size: 13px;
}

.result-images-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;

  .grid-image {
    text-align: center;
    cursor: pointer;

    img {
      width: 100%;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.8;
      }
    }

    .image-name {
      display: block;
      font-size: 11px;
      color: #909399;
      margin-top: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.result-stats {
  flex: 0 0 180px;

  .stat-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
  }

  .stat-label {
    color: #909399;
  }

  .stat-value {
    font-weight: 600;
    color: #303133;
  }
}

.video-result {
  flex: 1;
  min-width: 0;
}

.video-info {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.video-player {
  video {
    width: 100%;
    max-height: 360px;
    border-radius: 8px;
    background: #000;
  }
}

.fallback-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.frames-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.frame-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: opacity 0.2s;
}

.frame-card:hover {
  opacity: 0.8;
}

.frame-card img {
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.frame-info {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  font-size: 12px;
  color: #666;
  background: #fafafa;
}
</style>
```
**当前版本（缺失/被改）**：
```vue
<template>
  <div class="detection-result-card">
    <div class="card-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>检测结果</span>
      <el-tag size="small" type="success">
        {{ totalObjects }} 个目标
      </el-tag>
    </div>

    <div class="card-body">
      <!-- 单图模式：标注图 -->
      <div class="result-image" v-if="annotatedImageSrc && !isBatch">
        <img
          :src="annotatedImageSrc"
          alt="检测标注图"
          @click="showFullImage = true"
        />
      </div>

      <!-- 批量模式：多图展示 -->
      <div class="result-images-grid" v-if="isBatch && batchImages.length > 0">
        <div
          v-for="(img, index) in batchImages"
          :key="index"
          class="grid-image"
          @click="previewImage(img)"
        >
          <img :src="img.src" :alt="img.name" />
          <span class="image-name">{{ img.name }}</span>
        </div>
      </div>

      <!-- 视频检测结果：标注视频播放器 -->
      <div
        v-if="result.type === 'video'"
        class="video-result"
      >
        <div class="video-info">
          <el-tag type="info">时长: {{ result.duration_seconds }}s</el-tag>
          <el-tag type="info">FPS: {{ result.fps }}</el-tag>
          <el-tag type="info">采样帧: {{ result.processed_frames }}</el-tag>
          <el-tag type="success">目标: {{ totalObjects }}</el-tag>
        </div>
        <div v-if="result.annotated_video_url" class="video-player">
          <video
            :src="result.annotated_video_url"
            controls
            preload="metadata"
          ></video>
        </div>
        <div v-else-if="result.key_frames" class="frames-fallback">
          <p class="fallback-hint">标注视频生成中或上传失败，以下为关键帧预览：</p>
          <div class="frames-container">
            <div
              v-for="(frame, index) in thumbnailFrames"
              :key="index"
              class="frame-card"
              @click="previewVideoFrame(frame)"
            >
              <img
                :src="`data:image/jpeg;base64,${frame.annotated_image_base64}`"
                :alt="`帧 ${frame.frame_index}`"
              />
              <div class="frame-info">
                <span>{{ frame.timestamp }}s</span>
                <span>{{ frame.object_count }} 个目标</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">推理耗时</span>
          <span class="stat-value">{{ result.inference_time || result.total_inference_time || 0 }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">检测目标</span>
          <span class="stat-value">{{ totalObjects }} 个</span>
        </div>
        <div class="stat-item" v-if="isBatch">
          <span class="stat-label">图片数量</span>
          <span class="stat-value">{{ result.total_images ?? batchImages.length }} 张</span>
        </div>

        <!-- 类别统计表格 -->
        <el-table
          v-if="classCountsArray.length > 0"
          :data="classCountsArray"
          size="small"
          style="margin-top: 12px"
        >
          <el-table-column prop="className" label="类别" />
          <el-table-column prop="count" label="数量" width="80" />
        </el-table>
      </div>
    </div>

    <!-- 全屏图片预览 -->
    <el-dialog v-model="showFullImage" title="检测标注图" width="80%">
      <img
        v-if="previewSrc"
        :src="previewSrc"
        style="width: 100%"
        alt="检测标注图"
      />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * DetectionResultCard — 检测结果卡片组件
 *
 * 在对话消息中展示检测结果，包含：
 *   - 标注图预览（单图/批量多图，点击可放大）
 *   - 目标总数和推理耗时
 *   - 各类别数量统计表格
 */
import { DataAnalysis } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
});

const showFullImage = ref(false);
const previewSrc = ref(null);

/** 判断是否为批量检测结果 */
const isBatch = computed(() => {
  return Array.isArray(props.result.annotated_images) && props.result.annotated_images.length > 0;
});

/** 单图模式：标注图 URL（优先使用 MinIO URL，否则用 base64） */
const annotatedImageSrc = computed(() => {
  if (props.result.annotated_image_url) {
    return props.result.annotated_image_url;
  }
  if (props.result.annotated_image_base64) {
    return `data:image/jpeg;base64,${props.result.annotated_image_base64}`;
  }
  return null;
});

/** 批量模式：标注图列表 */
const batchImages = computed(() => {
  if (!isBatch.value) return [];
  return props.result.annotated_images.map((img) => ({
    name: img.image_path || "image",
    src: `data:image/jpeg;base64,${img.annotated_image_base64}`,
  }));
});

/** 点击预览图片 */
function previewImage(img) {
  previewSrc.value = img.src;
  showFullImage.value = true;
}

/** 视频模式：缩略帧列表（限制显示数量） */
const thumbnailFrames = computed(() => {
  const frames = props.result.key_frames || [];
  return frames.slice(0, 6);
});

/** 点击预览视频帧 */
function previewVideoFrame(frame) {
  previewSrc.value = `data:image/jpeg;base64,${frame.annotated_image_base64}`;
  showFullImage.value = true;
}

/** 目标总数（兼容多种后端字段名） */
const totalObjects = computed(() => {
  return props.result.total_objects
    ?? (props.result.fire_object_count || 0) + (props.result.smoke_object_count || 0)
    ?? 0;
});

/** 类别统计转为数组（用于 el-table，兼容 data.class_counts） */
const classCountsArray = computed(() => {
  const counts = props.result.class_counts || props.result.data?.class_counts || {};
  return Object.entries(counts).map(([className, count]) => ({
    className,
    count,
  }));
});
</script>

<style lang="scss" scoped>
.detection-result-card {
  margin-top: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 600;
  font-size: 14px;
}

.card-body {
  display: flex;
  gap: 16px;
  padding: 12px;
}

.result-image {
  flex: 1;
  min-width: 0;

  img {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }
  }
}

.result-images-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;

  .grid-image {
    text-align: center;
    cursor: pointer;

    img {
      width: 100%;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.8;
      }
    }

    .image-name {
      display: block;
      font-size: 11px;
      color: #909399;
      margin-top: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.result-stats {
  flex: 0 0 180px;

  .stat-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
  }

  .stat-label {
    color: #909399;
  }

  .stat-value {
    font-weight: 600;
    color: #303133;
  }
}

.video-result {
  flex: 1;
  min-width: 0;
}

.video-info {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.video-player {
  video {
    width: 100%;
    max-height: 360px;
    border-radius: 8px;
    background: #000;
  }
}

.fallback-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.frames-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.frame-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: opacity 0.2s;
}

.frame-card:hover {
  opacity: 0.8;
}

.frame-card img {
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.frame-info {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  font-size: 12px;
  color: #666;
  background: #fafafa;
}
</style>
```
**统一差异（unified diff）**：
```diff
--- backup/frontend/src/components/DetectionResultCard.vue
+++ current/frontend/src/components/DetectionResultCard.vue
@@ -1,5 +1,5 @@
 <template>
-  <div v-if="isValidResult" class="detection-result-card">
+  <div class="detection-result-card">
     <div class="card-header">
       <el-icon><DataAnalysis /></el-icon>
       <span>检测结果</span>
@@ -16,12 +16,6 @@
           alt="检测标注图"
           @click="showFullImage = true"
         />
-      </div>
-
-      <!-- 单图模式：无可用标注图占位 -->
-      <div class="result-image-placeholder" v-else-if="!isBatch && result.type !== 'video'">
-        <el-icon><Picture /></el-icon>
-        <span>标注图暂不可用</span>
       </div>
 
       <!-- 批量模式：多图展示 -->
@@ -126,7 +120,7 @@
  *   - 目标总数和推理耗时
  *   - 各类别数量统计表格
  */
-import { DataAnalysis, Picture } from "@element-plus/icons-vue";
+import { DataAnalysis } from "@element-plus/icons-vue";
 import { computed, ref } from "vue";
 
 const props = defineProps({
@@ -139,24 +133,18 @@
 const showFullImage = ref(false);
 const previewSrc = ref(null);
 
-/** 结果是否为合法对象 */
-const isValidResult = computed(() => {
-  return props.result && typeof props.result === 'object';
-});
-
 /** 判断是否为批量检测结果 */
 const isBatch = computed(() => {
-  return Array.isArray(props.result?.annotated_images) && props.result.annotated_images.length > 0;
-});
-
-/** 单图模式：标注图（优先使用 base64，避免 MinIO 预签名 URL 403） */
+  return Array.isArray(props.result.annotated_images) && props.result.annotated_images.length > 0;
+});
+
+/** 单图模式：标注图 URL（优先使用 MinIO URL，否则用 base64） */
 const annotatedImageSrc = computed(() => {
-  if (!isValidResult.value) return null;
+  if (props.result.annotated_image_url) {
+    return props.result.annotated_image_url;
+  }
   if (props.result.annotated_image_base64) {
     return `data:image/jpeg;base64,${props.result.annotated_image_base64}`;
-  }
-  if (props.result.annotated_image_url) {
-    return props.result.annotated_image_url;
   }
   return null;
 });
@@ -188,10 +176,11 @@
   showFullImage.value = true;
 }
 
-/** 目标总数（兼容 total_objects 与 fire_object_count + smoke_object_count） */
+/** 目标总数（兼容多种后端字段名） */
 const totalObjects = computed(() => {
   return props.result.total_objects
-    ?? ((props.result.fire_object_count || 0) + (props.result.smoke_object_count || 0));
+    ?? (props.result.fire_object_count || 0) + (props.result.smoke_object_count || 0)
+    ?? 0;
 });
 
 /** 类别统计转为数组（用于 el-table，兼容 data.class_counts） */
@@ -247,22 +236,6 @@
   }
 }
 
-.result-image-placeholder {
-  flex: 1;
-  min-width: 0;
-  display: flex;
-  flex-direction: column;
-  align-items: center;
-  justify-content: center;
-  gap: 8px;
-  min-height: 160px;
-  background: #fafafa;
-  border: 1px dashed #dcdfe6;
-  border-radius: 4px;
-  color: #909399;
-  font-size: 13px;
-}
-
 .result-images-grid {
   flex: 1;
   min-width: 0;
```
**结论**：优先使用 base64 标注图以避免 MinIO 预签名 URL 403 问题。


---

### 文件：frontend/src/utils/stream.js
**优先级**：P1
**影响说明**：SSE 流式处理工具变化，影响事件解析、token 读取、错误回调。
**备份版本（原功能）**：
```javascript
/**
 * SSE (Server-Sent Events) 流式处理工具
 * 用于 Day 11 智能体对话的流式渲染
 *
 * 支持的事件类型：
 *   - thinking    — Agent 正在思考
 *   - tool_start  — 开始调用工具
 *   - tool_end    — 工具调用完成
 *   - text_chunk  — 流式文本片段
 *   - done        — 完成（带完整响应）
 *   - error       — 错误信息
 *
 * 使用方式：
 *   const stop = streamChat(
 *     '/api/chat/messages/stream',
 *     { message: '你好' },
 *     {
 *       onMessage: (data) => { // 处理各类事件 },
 *       onDone: () => { console.log('完成') },
 *       onError: (err) => { console.error(err) },
 *     }
 *   )
 */

/**
 * 发起 SSE 流式请求
 *
 * @param {string} url - 请求地址（相对路径，会经过 Vite proxy）
 * @param {Object} body - 请求体
 * @param {Object} callbacks - 回调函数
 * @param {Function} callbacks.onMessage - 收到解析后事件对象的回调，参数 { type, content, tool, ... }
 * @param {Function} callbacks.onDone - 流结束时的回调
 * @param {Function} callbacks.onError - 错误时的回调
 * @returns {Function} stop - 调用此函数可中断连接
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks;

  // 从 localStorage 获取 Token（与 request.js 统一使用 "token" 字段名）
  const token = localStorage.getItem("rsod_token");

  // 使用 fetch + ReadableStream 实现 SSE
  const controller = new AbortController();

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // 缓冲区：用于拼接跨 chunk 的不完整 SSE 消息
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 流结束，处理缓冲区剩余数据
          if (buffer.trim()) {
            processSSEMessage(buffer, onMessage);
          }
          onDone?.();
          break;
        }

        // 解码并追加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割完整的 SSE 消息
        const messages = buffer.split("\n\n");

        // 最后一个元素可能是不完整的，保留在缓冲区
        buffer = messages.pop() || "";

        // 处理完整的消息
        for (const msg of messages) {
          if (msg.trim()) {
            const shouldStop = processSSEMessage(msg, onMessage);
            if (shouldStop) {
              onDone?.();
              return;
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  // 返回中断函数
  return () => controller.abort();
}

/**
 * 处理单条 SSE 消息
 *
 * 支持的 SSE 事件格式：
 *   event: thinking
 *   data: {"type":"thinking","content":"正在分析..."}
 *
 *   event: tool_start
 *   data: {"type":"tool_start","tool":"image_detect","input":{...}}
 *
 *   event: tool_end
 *   data: {"type":"tool_end","tool":"image_detect","result":"..."}
 *
 *   event: text_chunk
 *   data: {"type":"text_chunk","content":"检测到..."}
 *
 *   event: done
 *   data: {"type":"done","response":"..."}
 *
 *   event: error
 *   data: {"type":"error","content":"错误信息..."}
 *
 * @param {string} message - 完整的 SSE 消息（可能包含多行 data: 和 event:）
 * @param {Function} onMessage - 消息回调，接收解析后的事件对象
 * @returns {boolean} 是否应该停止（遇到 [DONE] 或 done 事件）
 */
function processSSEMessage(message, onMessage) {
  const lines = message.split("\n");

  let eventType = null;
  let eventData = null;

  for (const line of lines) {
    // 解析 event: 行
    if (line.startsWith("event: ")) {
      eventType = line.slice(7).trim();
    }

    // 解析 data: 行
    if (line.startsWith("data: ")) {
      const data = line.slice(6); // 去掉 "data: " 前缀

      // 遇到 [DONE] 标记，停止流
      if (data === "[DONE]") {
        return true;
      }

      try {
        eventData = JSON.parse(data);
      } catch {
        // JSON 解析失败，作为纯文本处理
        console.warn("[SSE] JSON解析失败，数据长度:", data.length);
        eventData = { type: eventType || "text_chunk", content: data };
      }
    }
  }

  // 如果 data 中没有 type 字段，用 event 行的值补充
  if (eventData) {
    if (!eventData.type && eventType) {
      eventData.type = eventType;
    }

    // error 事件兼容旧版 message 字段，并确保 content 不为 undefined
    if (eventData.type === "error") {
      eventData.content = eventData.content ?? eventData.message ?? "";
    }

    onMessage?.(eventData);

    // 遇到 done 事件，停止流
    if (eventData.type === "done") {
      return true;
    }
  }

  return false;
}
```
**当前版本（缺失/被改）**：
```javascript
/**
 * SSE (Server-Sent Events) 流式处理工具
 * 用于 Day 11 智能体对话的流式渲染
 *
 * 支持的事件类型：
 *   - thinking    — Agent 正在思考
 *   - tool_start  — 开始调用工具
 *   - tool_end    — 工具调用完成
 *   - text_chunk  — 流式文本片段
 *   - done        — 完成（带完整响应）
 *   - error       — 错误信息
 *
 * 使用方式：
 *   const stop = streamChat(
 *     '/api/chat/messages/stream',
 *     { message: '你好' },
 *     {
 *       onMessage: (data) => { // 处理各类事件 },
 *       onDone: () => { console.log('完成') },
 *       onError: (err) => { console.error(err) },
 *     }
 *   )
 */

/**
 * 发起 SSE 流式请求
 *
 * @param {string} url - 请求地址（相对路径，会经过 Vite proxy）
 * @param {Object} body - 请求体
 * @param {Object} callbacks - 回调函数
 * @param {Function} callbacks.onMessage - 收到解析后事件对象的回调，参数 { type, content, tool, ... }
 * @param {Function} callbacks.onDone - 流结束时的回调
 * @param {Function} callbacks.onError - 错误时的回调
 * @returns {Function} stop - 调用此函数可中断连接
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks;

  // 从 localStorage 获取 Token（与 request.js 统一使用 "token" 字段名）
  const token = localStorage.getItem("rsod_token");

  // 使用 fetch + ReadableStream 实现 SSE
  const controller = new AbortController();

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // 缓冲区：用于拼接跨 chunk 的不完整 SSE 消息
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 流结束，处理缓冲区剩余数据
          if (buffer.trim()) {
            processSSEMessage(buffer, onMessage);
          }
          onDone?.();
          break;
        }

        // 解码并追加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割完整的 SSE 消息
        const messages = buffer.split("\n\n");

        // 最后一个元素可能是不完整的，保留在缓冲区
        buffer = messages.pop() || "";

        // 处理完整的消息
        for (const msg of messages) {
          if (msg.trim()) {
            const shouldStop = processSSEMessage(msg, onMessage);
            if (shouldStop) {
              onDone?.();
              return;
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  // 返回中断函数
  return () => controller.abort();
}

/**
 * 处理单条 SSE 消息
 *
 * 支持的 SSE 事件格式：
 *   event: thinking
 *   data: {"type":"thinking","content":"正在分析..."}
 *
 *   event: tool_start
 *   data: {"type":"tool_start","tool":"image_detect","input":{...}}
 *
 *   event: tool_end
 *   data: {"type":"tool_end","tool":"image_detect","result":"..."}
 *
 *   event: text_chunk
 *   data: {"type":"text_chunk","content":"检测到..."}
 *
 *   event: done
 *   data: {"type":"done","response":"..."}
 *
 *   event: error
 *   data: {"type":"error","content":"错误信息..."}
 *
 * @param {string} message - 完整的 SSE 消息（可能包含多行 data: 和 event:）
 * @param {Function} onMessage - 消息回调，接收解析后的事件对象
 * @returns {boolean} 是否应该停止（遇到 [DONE] 或 done 事件）
 */
function processSSEMessage(message, onMessage) {
  const lines = message.split("\n");

  let eventType = null;
  let eventData = null;

  for (const line of lines) {
    // 解析 event: 行
    if (line.startsWith("event: ")) {
      eventType = line.slice(7).trim();
    }

    // 解析 data: 行
    if (line.startsWith("data: ")) {
      const data = line.slice(6); // 去掉 "data: " 前缀

      // 遇到 [DONE] 标记，停止流
      if (data === "[DONE]") {
        return true;
      }

      try {
        eventData = JSON.parse(data);
      } catch {
        // JSON 解析失败，作为纯文本处理
        console.warn("[SSE] JSON解析失败，数据长度:", data.length);
        eventData = { type: eventType || "text_chunk", content: data };
      }
    }
  }

  // 如果 data 中没有 type 字段，用 event 行的值补充
  if (eventData) {
    if (!eventData.type && eventType) {
      eventData.type = eventType;
    }
    onMessage?.(eventData);

    // 遇到 done 事件，停止流
    if (eventData.type === "done") {
      return true;
    }
  }

  return false;
}
```
**统一差异（unified diff）**：
```diff
--- backup/frontend/src/utils/stream.js
+++ current/frontend/src/utils/stream.js
@@ -166,12 +166,6 @@
     if (!eventData.type && eventType) {
       eventData.type = eventType;
     }
-
-    // error 事件兼容旧版 message 字段，并确保 content 不为 undefined
-    if (eventData.type === "error") {
-      eventData.content = eventData.content ?? eventData.message ?? "";
-    }
-
     onMessage?.(eventData);
 
     // 遇到 done 事件，停止流
```
**结论**：统一 localStorage token key 与后端一致，正确解析各类型 SSE 事件（含 error 事件 message 兼容）。


---

### 文件：backend/.env.example
**说明**：两个版本内容完全一致，无差异。


---

### 文件：backend/app/agent/prompts.py
**说明**：两个版本内容完全一致，无差异。


---

### 文件：backend/app/config/settings.py
**说明**：两个版本内容完全一致，无差异。


---

### 文件：backend/app/core/llm_client.py
**说明**：备份版本与当前版本均不存在该文件。


---

### 文件：backend/app/core/llm_service.py
**说明**：备份版本与当前版本均不存在该文件。


---

### 文件：backend/app/entity/db_models.py
**说明**：两个版本内容完全一致，无差异。


---

### 文件：backend/app/entity/schemas.py
**说明**：两个版本内容完全一致，无差异。


---

### 文件：frontend/src/api/chat.js
**说明**：备份版本与当前版本均不存在该文件。


---
