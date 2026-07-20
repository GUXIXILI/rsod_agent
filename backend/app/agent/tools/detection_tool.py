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

# ══════════════════════════════════════════════════════════════
# 检测参数兜底常量（避免过度识别导致 token 溢出）
# ══════════════════════════════════════════════════════════════
_DEFAULT_CONF = 0.4       # 默认置信度阈值（火焰烟雾检测建议 ≥ 0.35）
_DEFAULT_IOU = 0.3        # 默认 NMS IoU 阈值（降低重叠框）
_MIN_CONF = 0.05          # 置信度下限（低于此值强制使用默认值）
_MIN_IOU = 0.05           # IoU 下限
_MAX_THRESHOLD = 0.95     # 阈值上限


def _validate_thresholds(conf: float, iou: float) -> tuple:
    """校验并标准化 conf/iou 参数，防止 LLM 传入无效值导致过度识别。

    如果 LLM 传入字符串（如 "0"）或极端值，强制修正为安全的默认值。
    """
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        logger.warning("conf 参数类型错误，已修正为默认值 %.2f", _DEFAULT_CONF)
        conf = _DEFAULT_CONF

    try:
        iou = float(iou)
    except (TypeError, ValueError):
        logger.warning("iou 参数类型错误，已修正为默认值 %.2f", _DEFAULT_IOU)
        iou = _DEFAULT_IOU

    # 限制在合理范围内
    conf = max(0.001, min(conf, _MAX_THRESHOLD))
    iou = max(0.001, min(iou, _MAX_THRESHOLD))

    # 过低阈值强制修正（避免 LLM 传入 0 导致完全不过滤）
    if conf < _MIN_CONF:
        logger.warning("conf=%.4f 过低，已修正为默认值 %.2f", conf, _DEFAULT_CONF)
        conf = _DEFAULT_CONF
    if iou < _MIN_IOU:
        logger.warning("iou=%.4f 过低，已修正为默认值 %.2f", iou, _DEFAULT_IOU)
        iou = _DEFAULT_IOU

    return conf, iou


@tool
def detect_single_image(
    image_path: str,
    conf: float = 0.4,
    iou: float = 0.3,
) -> str:
    """对单张图片进行火焰和烟雾目标检测。

    适用场景：用户上传单张图片，需要检测其中是否存在火焰或烟雾。

    Args:
        image_path: 图片文件的本地路径或 MinIO URL。
        conf: 置信度阈值（0.0~1.0），默认 0.4。低于此值的检测结果会被过滤。
        iou: NMS（非极大值抑制）IoU 阈值（0.0~1.0），默认 0.3。用于去除重叠框。

    Returns:
        str: JSON 格式的检测结果，包含文字摘要、标注图 URL/base64、检测框列表等。
    """
    # 校验并标准化参数，防止 LLM 传入无效值导致过度识别
    conf, iou = _validate_thresholds(conf, iou)

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

            return json.dumps({
                "tool": "detect_batch_images",
                "status": "success",
                "summary": "\n".join(result_lines),
                "data": {
                    "total": total,
                    "fire_detected": fire_detected,
                    "smoke_detected": smoke_detected,
                    "warning_count": warning_count
                }
            }, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.exception("批量检测工具调用失败")
        return json.dumps({
            "tool": "detect_batch_images",
            "status": "error",
            "summary": f"批量检测失败：{str(e)}"
        }, ensure_ascii=False)


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

            return json.dumps({
                "tool": "detect_zip_images_file",
                "status": "success",
                "summary": "\n".join(result_lines),
                "data": {
                    "total": total,
                    "fire_detected": fire_detected,
                    "smoke_detected": smoke_detected,
                    "warning_count": warning_count
                }
            }, ensure_ascii=False)
        finally:
            db.close()
    except FileNotFoundError:
        return json.dumps({
            "tool": "detect_zip_images_file",
            "status": "error",
            "summary": f"找不到 ZIP 文件 '{zip_path}'，请确认文件路径是否正确。"
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("ZIP 批量检测工具调用失败: zip_path=%s", zip_path)
        return json.dumps({
            "tool": "detect_zip_images_file",
            "status": "error",
            "summary": f"ZIP 批量检测失败：{str(e)}"
        }, ensure_ascii=False)


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

            return json.dumps({
                "tool": "detect_video_file",
                "status": "success",
                "summary": "\n".join(result_lines),
                "data": {
                    "fire_count": fire_count,
                    "smoke_count": smoke_count,
                    "fire_level": fire_level,
                    "duration": duration,
                    "frame_sample_rate": frame_sample_rate
                }
            }, ensure_ascii=False)
        finally:
            db.close()
    except FileNotFoundError:
        return json.dumps({
            "tool": "detect_video_file",
            "status": "error",
            "summary": f"找不到视频文件 '{video_path}'，请确认文件路径是否正确。"
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("视频检测工具调用失败: video_path=%s", video_path)
        return json.dumps({
            "tool": "detect_video_file",
            "status": "error",
            "summary": f"视频检测失败：{str(e)}"
        }, ensure_ascii=False)