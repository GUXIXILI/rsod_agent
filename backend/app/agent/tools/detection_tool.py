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