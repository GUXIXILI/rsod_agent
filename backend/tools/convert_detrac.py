"""
DETRAC 数据集转换工具

将 DETRAC 数据集（XML 标注格式）转换为 YOLO TXT 格式，并划分训练/验证/测试集。

用法：
    python tools/convert_detrac.py --input_dir <DETRAC原始目录> --output_dir <YOLO输出目录>

数据集划分比例默认为 8:1:1（训练:验证:测试）。
"""
import argparse
import os
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 默认数据集划分比例
DEFAULT_SPLIT_RATIOS = (0.8, 0.1, 0.1)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="DETRAC 数据集转 YOLO 格式")
    parser.add_argument(
        "--input_dir",
        required=True,
        help="DETRAC 原始数据集目录（包含 XML 标注和图片）",
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="YOLO 格式输出目录",
    )
    parser.add_argument(
        "--split_ratios",
        type=float,
        nargs=3,
        default=DEFAULT_SPLIT_RATIOS,
        help="数据集划分比例（训练 验证 测试），默认 0.8 0.1 0.1",
    )
    return parser.parse_args()


def parse_detrac_xml(xml_path: str) -> List[Dict]:
    """
    解析 DETRAC XML 标注文件

    DETRAC 标注格式示例：
    <frame number="0">
        <target id="1">
            <box left="100" top="200" width="80" height="120"/>
            <attribute orientation="front" speed="45" trajectory="straight" vehicle_type="car"/>
        </target>
    </frame>

    返回帧列表，每帧包含目标列表。
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    frames = []
    for frame_elem in root.findall("frame"):
        frame_num = int(frame_elem.get("number", 0))
        targets = []

        for target_elem in frame_elem.findall("target"):
            box_elem = target_elem.find("box")
            attr_elem = target_elem.find("attribute")

            if box_elem is None:
                continue

            # 解析边界框
            left = float(box_elem.get("left", 0))
            top = float(box_elem.get("top", 0))
            width = float(box_elem.get("width", 0))
            height = float(box_elem.get("height", 0))

            # 解析属性
            orientation = attr_elem.get("orientation", "unknown") if attr_elem is not None else "unknown"
            speed = float(attr_elem.get("speed", 0)) if attr_elem is not None else 0.0
            trajectory = attr_elem.get("trajectory", "unknown") if attr_elem is not None else "unknown"
            vehicle_type = attr_elem.get("vehicle_type", "unknown") if attr_elem is not None else "unknown"

            targets.append({
                "bbox": (left, top, width, height),
                "orientation": orientation,
                "speed": speed,
                "trajectory": trajectory,
                "vehicle_type": vehicle_type,
            })

        frames.append({
            "frame_num": frame_num,
            "targets": targets,
        })

    return frames


def bbox_to_yolo(bbox: Tuple[float, ...], img_width: int, img_height: int) -> Tuple[float, ...]:
    """
    将 DETRAC 边界框（left, top, width, height）转换为 YOLO 归一化格式（cx, cy, w, h）

    YOLO 格式：cx = (left + width/2) / img_width, cy = (top + height/2) / img_height,
               w = width / img_width, h = height / img_height
    """
    left, top, width, height = bbox
    cx = (left + width / 2) / img_width
    cy = (top + height / 2) / img_height
    nw = width / img_width
    nh = height / img_height
    return (cx, cy, nw, nh)


def split_dataset(file_list: List[str], ratios: Tuple[float, ...]) -> Dict[str, List[str]]:
    """
    按比例随机划分数据集

    返回 {"train": [...], "val": [...], "test": [...]}
    """
    random.seed(42)
    random.shuffle(file_list)

    total = len(file_list)
    train_end = int(total * ratios[0])
    val_end = train_end + int(total * ratios[1])

    return {
        "train": file_list[:train_end],
        "val": file_list[train_end:val_end],
        "test": file_list[val_end:],
    }


def main():
    """主流程：读取 DETRAC 标注 → 转换为 YOLO 格式 → 划分数据集 → 生成 data.yaml"""
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"错误：输入目录不存在: {input_dir}")
        return

    # 查找 XML 标注文件
    xml_files = list(input_dir.glob("*.xml"))
    if not xml_files:
        print(f"错误：在 {input_dir} 中未找到 XML 标注文件")
        return

    print(f"找到 {len(xml_files)} 个 XML 标注文件")

    # 创建输出目录结构
    for subset in ["train", "val", "test"]:
        (output_dir / "images" / subset).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / subset).mkdir(parents=True, exist_ok=True)

    # 数据集划分
    xml_names = [f.stem for f in xml_files]
    splits = split_dataset(xml_names, args.split_ratios)

    print(f"数据集划分: 训练={len(splits['train'])}, 验证={len(splits['val'])}, 测试={len(splits['test'])}")

    # 类别映射（DETRAC 常见车辆类型 → YOLO class_id）
    # 后续可扩展更多类别
    vehicle_type_to_id = {
        "car": 0,
        "bus": 1,
        "van": 2,
        "others": 3,
    }

    total_converted = 0

    for subset, names in splits.items():
        for name in names:
            xml_path = input_dir / f"{name}.xml"
            frames = parse_detrac_xml(str(xml_path))

            for frame in frames:
                frame_num = frame["frame_num"]
                # 图片文件名格式：{name}_img{frame_num:05d}.jpg
                img_name = f"{name}_img{frame_num:05d}.jpg"
                label_name = f"{name}_img{frame_num:05d}.txt"

                img_src = input_dir / img_name
                img_dst = output_dir / "images" / subset / img_name
                label_dst = output_dir / "labels" / subset / label_name

                # 复制图片（如果存在）
                if img_src.exists():
                    import shutil
                    shutil.copy2(img_src, img_dst)

                # 写入 YOLO 标注
                if frame["targets"]:
                    # 图片尺寸需要从实际图片获取，这里使用默认值
                    img_width = 960   # DETRAC 常见分辨率
                    img_height = 540

                    with open(label_dst, "w", encoding="utf-8") as f:
                        for target in frame["targets"]:
                            vehicle_type = target["vehicle_type"]
                            class_id = vehicle_type_to_id.get(vehicle_type, 3)  # 未知类型归为 others

                            cx, cy, nw, nh = bbox_to_yolo(target["bbox"], img_width, img_height)

                            # 坐标裁剪到 [0, 1]
                            cx = max(0, min(1, cx))
                            cy = max(0, min(1, cy))
                            nw = max(0, min(1, nw))
                            nh = max(0, min(1, nh))

                            f.write(f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

                    total_converted += len(frame["targets"])

    # 生成 data.yaml
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"# DETRAC 数据集配置（自动生成）\n")
        f.write(f"path: {output_dir.resolve()}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        f.write(f"test: images/test\n")
        f.write(f"nc: {len(vehicle_type_to_id)}\n")
        f.write(f"names: {list(vehicle_type_to_id.keys())}\n")

    print(f"转换完成: 共 {total_converted} 个目标，输出目录: {output_dir}")


if __name__ == "__main__":
    main()