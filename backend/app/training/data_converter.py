"""
数据集格式转换器

将 VOC XML、COCO JSON、LabelMe JSON 三种标注格式统一转换为 YOLO TXT 格式。
YOLO 格式：每行 <class_id> <x_center> <y_center> <width> <height>，坐标归一化到 [0,1] 区间，保留 6 位小数。
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

from app.core.logger import get_logger

logger = get_logger(__name__)

# YOLO 坐标归一化后保留的小数位数
_YOLO_DECIMAL_PLACES = 6


def _clip_bbox(x_center: float, y_center: float, w: float, h: float) -> tuple:
    """
    将 YOLO 归一化坐标裁剪到 [0, 1] 区间，防止浮点误差导致越界。

    参数：
        x_center: 归一化中心 x 坐标
        y_center: 归一化中心 y 坐标
        w:        归一化边界框宽度
        h:        归一化边界框高度

    返回：
        (x_center, y_center, w, h) 裁剪后的元组
    """
    # 先裁剪宽高，再根据宽高限制中心点范围，确保整个框不超出 [0,1]
    w = max(0.0, min(w, 1.0))
    h = max(0.0, min(h, 1.0))
    half_w = w / 2.0
    half_h = h / 2.0
    x_center = max(half_w, min(x_center, 1.0 - half_w))
    y_center = max(half_h, min(y_center, 1.0 - half_h))
    return x_center, y_center, w, h


def _format_yolo_line(class_id: int, x_center: float, y_center: float, w: float, h: float) -> str:
    """
    格式化单行 YOLO 标注。

    参数：
        class_id: 类别 ID（整数）
        x_center: 归一化中心 x 坐标
        y_center: 归一化中心 y 坐标
        w:        归一化边界框宽度
        h:        归一化边界框高度

    返回：
        格式化后的 YOLO 标注行字符串
    """
    return (
        f"{class_id} "
        f"{x_center:.{_YOLO_DECIMAL_PLACES}f} "
        f"{y_center:.{_YOLO_DECIMAL_PLACES}f} "
        f"{w:.{_YOLO_DECIMAL_PLACES}f} "
        f"{h:.{_YOLO_DECIMAL_PLACES}f}"
    )


class DataConverter:
    """数据集格式转换器，将多种标注格式统一转换为 YOLO TXT 格式。"""

    @staticmethod
    def voc_to_yolo(
        xml_dir: str,
        output_dir: str,
        class_mapping: Dict[str, int],
    ) -> Dict[str, int]:
        """
        将 VOC XML 标注转换为 YOLO TXT 格式。

        VOC XML 结构示例：
            <annotation>
                <size>
                    <width>1920</width>
                    <height>1080</height>
                </size>
                <object>
                    <name>person</name>
                    <bndbox>
                        <xmin>100</xmin>
                        <ymin>200</ymin>
                        <xmax>300</xmax>
                        <ymax>400</ymax>
                    </bndbox>
                </object>
            </annotation>

        参数：
            xml_dir:       存放 VOC XML 文件的目录路径
            output_dir:    输出 YOLO TXT 文件的目录路径
            class_mapping: 类别名称到类别 ID 的映射字典，如 {"person": 0, "car": 1}

        返回：
            统计信息字典：{"total": int, "converted": int, "skipped": int, "errors": int}
        """
        xml_dir = Path(xml_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": 0}

        if not xml_dir.is_dir():
            logger.error(f"VOC XML 目录不存在或不是目录: {xml_dir}")
            return stats

        xml_files = sorted(xml_dir.glob("*.xml"))
        stats["total"] = len(xml_files)

        if not xml_files:
            logger.warning(f"VOC XML 目录中没有找到 .xml 文件: {xml_dir}")
            return stats

        for xml_path in xml_files:
            try:
                tree = ET.parse(str(xml_path))
                root = tree.getroot()

                # 获取图像尺寸 —— YOLO 归一化必须的基准
                size_elem = root.find("size")
                if size_elem is None:
                    logger.warning(f"XML 缺少 <size> 元素，跳过: {xml_path.name}")
                    stats["skipped"] += 1
                    continue

                img_width_elem = size_elem.find("width")
                img_height_elem = size_elem.find("height")
                if img_width_elem is None or img_height_elem is None:
                    logger.warning(f"XML 缺少 <width> 或 <height> 子元素，跳过: {xml_path.name}")
                    stats["skipped"] += 1
                    continue

                img_width = float(img_width_elem.text)
                img_height = float(img_height_elem.text)

                # 图像尺寸为 0 或负数时无法归一化，跳过
                if img_width <= 0 or img_height <= 0:
                    logger.warning(f"XML 图像尺寸无效 (width={img_width}, height={img_height})，跳过: {xml_path.name}")
                    stats["skipped"] += 1
                    continue

                yolo_lines = []
                for obj in root.findall("object"):
                    name_elem = obj.find("name")
                    bndbox = obj.find("bndbox")

                    if name_elem is None or bndbox is None:
                        logger.warning(f"XML 中 object 缺少 <name> 或 <bndbox>，跳过该标注: {xml_path.name}")
                        continue

                    class_name = (name_elem.text or "").strip()
                    if not class_name:
                        logger.warning(f"XML 中 class_name 为空，跳过该标注: {xml_path.name}")
                        continue

                    # 类别不在映射表中则跳过该标注
                    if class_name not in class_mapping:
                        logger.warning(
                            f"类别 '{class_name}' 不在 class_mapping 中，跳过该标注: {xml_path.name}"
                        )
                        continue

                    class_id = class_mapping[class_name]

                    # 安全读取 bndbox 四个坐标值，任一缺失则跳过
                    xmin_elem = bndbox.find("xmin")
                    ymin_elem = bndbox.find("ymin")
                    xmax_elem = bndbox.find("xmax")
                    ymax_elem = bndbox.find("ymax")

                    if any(e is None for e in (xmin_elem, ymin_elem, xmax_elem, ymax_elem)):
                        logger.warning(f"XML 中 bndbox 坐标不完整，跳过该标注: {xml_path.name}")
                        continue

                    xmin = float(xmin_elem.text)
                    ymin = float(ymin_elem.text)
                    xmax = float(xmax_elem.text)
                    ymax = float(ymax_elem.text)

                    # 确保 xmin < xmax, ymin < ymax，交换错误顺序
                    if xmin > xmax:
                        xmin, xmax = xmax, xmin
                    if ymin > ymax:
                        ymin, ymax = ymax, ymin

                    # 转换为 YOLO 归一化坐标
                    x_center = (xmin + xmax) / 2.0 / img_width
                    y_center = (ymin + ymax) / 2.0 / img_height
                    w = (xmax - xmin) / img_width
                    h = (ymax - ymin) / img_height

                    # 裁剪到 [0,1] 区间，防止浮点精度导致越界
                    x_center, y_center, w, h = _clip_bbox(x_center, y_center, w, h)

                    # 跳过退化框（宽或高为 0）
                    if w <= 0 or h <= 0:
                        logger.warning(
                            f"边界框退化 (w={w:.6f}, h={h:.6f})，跳过该标注: {xml_path.name}"
                        )
                        continue

                    yolo_lines.append(_format_yolo_line(class_id, x_center, y_center, w, h))

                # 写入 YOLO TXT 文件（与 XML 同名，扩展名改为 .txt）
                txt_path = output_dir / f"{xml_path.stem}.txt"
                txt_path.write_text("\n".join(yolo_lines) + "\n" if yolo_lines else "", encoding="utf-8")
                stats["converted"] += 1
                logger.debug(f"VOC → YOLO 完成: {xml_path.name} → {txt_path.name} ({len(yolo_lines)} 个框)")

            except ET.ParseError:
                logger.error(f"XML 解析失败，文件可能损坏: {xml_path.name}")
                stats["errors"] += 1
            except Exception:
                logger.exception(f"VOC 转换异常: {xml_path.name}")
                stats["errors"] += 1

        logger.info(
            f"VOC → YOLO 转换完成: total={stats['total']}, converted={stats['converted']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']}"
        )
        return stats

    @staticmethod
    def coco_to_yolo(
        json_path: str,
        output_dir: str,
        class_mapping: Optional[Dict[str, int]] = None,
    ) -> Dict[str, int]:
        """
        将 COCO JSON 标注转换为 YOLO TXT 格式。

        COCO JSON 结构示例：
            {
                "images": [{"id": 1, "file_name": "img.jpg", "width": 1920, "height": 1080}],
                "annotations": [{"image_id": 1, "category_id": 1, "bbox": [x, y, w, h]}],
                "categories": [{"id": 1, "name": "person"}]
            }

        COCO bbox 格式为 [x_min, y_min, width, height]（像素坐标），
        不同于 VOC 的 [xmin, ymin, xmax, ymax]。

        参数：
            json_path:     COCO JSON 标注文件路径
            output_dir:    输出 YOLO TXT 文件的目录路径
            class_mapping: 类别名称到类别 ID 的映射字典。
                          为 None 时，按 categories 数组顺序自动编号（从 0 开始）。

        返回：
            统计信息字典：{"total": int, "converted": int, "skipped": int, "errors": int}
        """
        json_path = Path(json_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": 0}

        if not json_path.is_file():
            logger.error(f"COCO JSON 文件不存在: {json_path}")
            return stats

        # 读取并解析 JSON
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                coco_data = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"COCO JSON 解析失败，文件可能损坏: {json_path}")
            stats["errors"] += 1
            return stats
        except Exception:
            logger.exception(f"COCO JSON 读取异常: {json_path}")
            stats["errors"] += 1
            return stats

        # ── 构建 image_id → 图像信息 映射 ──
        images = coco_data.get("images", [])
        if not images:
            logger.warning(f"COCO JSON 中缺少 images 字段: {json_path}")
            return stats

        image_map: Dict[int, dict] = {}
        for img in images:
            img_id = img.get("id")
            if img_id is None:
                continue
            image_map[img_id] = img

        # ── 构建 category_id → 类别名称 映射 ──
        categories = coco_data.get("categories", [])
        cat_id_to_name: Dict[int, str] = {}
        for cat in categories:
            cid = cat.get("id")
            cname = cat.get("name", "").strip()
            if cid is not None and cname:
                cat_id_to_name[cid] = cname

        # ── 确定 class_mapping ──
        # 如果外部未提供，按 categories 数组出现顺序自动编号
        if class_mapping is None:
            class_mapping = {}
            for idx, cat in enumerate(categories):
                cname = cat.get("name", "").strip()
                if cname:
                    class_mapping[cname] = idx
            if class_mapping:
                logger.info(f"COCO 自动生成 class_mapping（共 {len(class_mapping)} 类）: {class_mapping}")

        if not class_mapping:
            logger.warning(f"COCO JSON 中无有效类别，转换终止: {json_path}")
            return stats

        # ── 按 image_id 分组标注 ──
        annotations = coco_data.get("annotations", [])
        ann_by_image: Dict[int, list] = {}
        for ann in annotations:
            img_id = ann.get("image_id")
            if img_id is None:
                continue
            ann_by_image.setdefault(img_id, []).append(ann)

        stats["total"] = len(ann_by_image)

        for img_id, anns in ann_by_image.items():
            img_info = image_map.get(img_id)
            if img_info is None:
                logger.warning(f"标注中的 image_id={img_id} 在 images 中找不到对应记录，跳过")
                stats["skipped"] += 1
                continue

            img_width = img_info.get("width", 0)
            img_height = img_info.get("height", 0)
            file_name = img_info.get("file_name", f"{img_id}")

            # 图像尺寸无效时跳过
            if not img_width or not img_height or img_width <= 0 or img_height <= 0:
                logger.warning(
                    f"图像尺寸无效 (width={img_width}, height={img_height})，"
                    f"跳过 image_id={img_id} ({file_name})"
                )
                stats["skipped"] += 1
                continue

            yolo_lines = []
            for ann in anns:
                category_id = ann.get("category_id")
                bbox = ann.get("bbox")

                if category_id is None or bbox is None:
                    continue

                # COCO bbox: [x_min, y_min, width, height]
                if len(bbox) != 4:
                    logger.warning(f"bbox 长度不为 4，跳过: image_id={img_id}, bbox={bbox}")
                    continue

                x_min, y_min, bbox_w, bbox_h = bbox

                # 跳过退化框
                if bbox_w <= 0 or bbox_h <= 0:
                    logger.warning(
                        f"退化边界框 (bbox_w={bbox_w}, bbox_h={bbox_h})，跳过: image_id={img_id}"
                    )
                    continue

                # 根据 category_id 获取类别名称，再映射到 class_id
                category_name = cat_id_to_name.get(category_id)
                if category_name is None:
                    logger.warning(f"未知 category_id={category_id}，跳过: image_id={img_id}")
                    continue
                if category_name not in class_mapping:
                    logger.warning(
                        f"类别 '{category_name}' 不在 class_mapping 中，跳过: image_id={img_id}"
                    )
                    continue

                class_id = class_mapping[category_name]

                # COCO → YOLO 坐标转换
                x_center = (x_min + bbox_w / 2.0) / img_width
                y_center = (y_min + bbox_h / 2.0) / img_height
                w = bbox_w / img_width
                h = bbox_h / img_height

                # 裁剪到 [0,1] 区间
                x_center, y_center, w, h = _clip_bbox(x_center, y_center, w, h)

                if w <= 0 or h <= 0:
                    logger.warning(
                        f"归一化后边界框退化 (w={w:.6f}, h={h:.6f})，跳过: image_id={img_id}"
                    )
                    continue

                yolo_lines.append(_format_yolo_line(class_id, x_center, y_center, w, h))

            # 输出文件名为去掉原扩展名后的 .txt
            txt_name = Path(file_name).stem + ".txt"
            txt_path = output_dir / txt_name
            txt_path.write_text("\n".join(yolo_lines) + "\n" if yolo_lines else "", encoding="utf-8")
            stats["converted"] += 1
            logger.debug(f"COCO → YOLO 完成: image_id={img_id} → {txt_name} ({len(yolo_lines)} 个框)")

        logger.info(
            f"COCO → YOLO 转换完成: total={stats['total']}, converted={stats['converted']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']}"
        )
        return stats

    @staticmethod
    def labelme_to_yolo(
        json_dir: str,
        output_dir: str,
        class_mapping: Dict[str, int],
    ) -> Dict[str, int]:
        """
        将 LabelMe JSON 标注转换为 YOLO TXT 格式。

        LabelMe JSON 结构示例：
            {
                "imageWidth": 1920,
                "imageHeight": 1080,
                "shapes": [
                    {
                        "label": "person",
                        "shape_type": "rectangle",
                        "points": [[xmin, ymin], [xmax, ymax]]
                    }
                ]
            }

        仅处理 shape_type 为 "rectangle" 的标注，多边形、圆形等其他形状会被忽略。

        参数：
            json_dir:      存放 LabelMe JSON 文件的目录路径
            output_dir:    输出 YOLO TXT 文件的目录路径
            class_mapping: 类别名称到类别 ID 的映射字典

        返回：
            统计信息字典：{"total": int, "converted": int, "skipped": int, "errors": int}
        """
        json_dir = Path(json_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": 0}

        if not json_dir.is_dir():
            logger.error(f"LabelMe JSON 目录不存在或不是目录: {json_dir}")
            return stats

        json_files = sorted(json_dir.glob("*.json"))
        stats["total"] = len(json_files)

        if not json_files:
            logger.warning(f"LabelMe JSON 目录中没有找到 .json 文件: {json_dir}")
            return stats

        for json_path in json_files:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"LabelMe JSON 解析失败: {json_path.name}")
                stats["errors"] += 1
                continue
            except Exception:
                logger.exception(f"LabelMe JSON 读取异常: {json_path.name}")
                stats["errors"] += 1
                continue

            # 获取图像尺寸 —— 归一化必需的基准
            img_width = data.get("imageWidth", 0)
            img_height = data.get("imageHeight", 0)

            if not img_width or not img_height or img_width <= 0 or img_height <= 0:
                logger.warning(
                    f"LabelMe JSON 图像尺寸无效 (imageWidth={img_width}, imageHeight={img_height})，"
                    f"跳过: {json_path.name}"
                )
                stats["skipped"] += 1
                continue

            shapes = data.get("shapes", [])
            if not shapes:
                logger.debug(f"LabelMe JSON 无 shapes 标注，跳过: {json_path.name}")
                stats["skipped"] += 1
                continue

            yolo_lines = []
            for shape in shapes:
                shape_type = shape.get("shape_type", "")
                # 仅处理矩形标注，忽略多边形、圆形等其他形状
                if shape_type != "rectangle":
                    continue

                label = shape.get("label", "").strip()
                if not label:
                    logger.warning(f"LabelMe shape 缺少 label 字段，跳过: {json_path.name}")
                    continue

                if label not in class_mapping:
                    logger.warning(
                        f"类别 '{label}' 不在 class_mapping 中，跳过: {json_path.name}"
                    )
                    continue

                class_id = class_mapping[label]

                points = shape.get("points", [])
                # LabelMe rectangle 的 points 格式: [[xmin, ymin], [xmax, ymax]]
                if len(points) != 2:
                    logger.warning(
                        f"LabelMe rectangle points 长度不为 2，跳过: {json_path.name}, label={label}"
                    )
                    continue

                (xmin, ymin), (xmax, ymax) = points

                # 确保 xmin < xmax, ymin < ymax
                if xmin > xmax:
                    xmin, xmax = xmax, xmin
                if ymin > ymax:
                    ymin, ymax = ymax, ymin

                # 转换为 YOLO 归一化坐标
                x_center = (xmin + xmax) / 2.0 / img_width
                y_center = (ymin + ymax) / 2.0 / img_height
                w = (xmax - xmin) / img_width
                h = (ymax - ymin) / img_height

                # 裁剪到 [0,1] 区间
                x_center, y_center, w, h = _clip_bbox(x_center, y_center, w, h)

                if w <= 0 or h <= 0:
                    logger.warning(
                        f"边界框退化 (w={w:.6f}, h={h:.6f})，跳过: {json_path.name}, label={label}"
                    )
                    continue

                yolo_lines.append(_format_yolo_line(class_id, x_center, y_center, w, h))

            # 输出文件名为与 JSON 同名的 .txt
            txt_path = output_dir / f"{json_path.stem}.txt"
            txt_path.write_text("\n".join(yolo_lines) + "\n" if yolo_lines else "", encoding="utf-8")
            stats["converted"] += 1
            logger.debug(f"LabelMe → YOLO 完成: {json_path.name} → {txt_path.name} ({len(yolo_lines)} 个框)")

        logger.info(
            f"LabelMe → YOLO 转换完成: total={stats['total']}, converted={stats['converted']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']}"
        )
        return stats