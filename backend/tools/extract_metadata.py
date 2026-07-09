"""
DETRAC 元数据提取工具

从 DETRAC XML 标注文件中提取车辆运动属性（车速、车型、朝向、轨迹），
输出为 JSONL 格式，供 traffic_service 导入数据库。

用法：
    python tools/extract_metadata.py --input_dir <DETRAC目录> --output_file <输出JSONL路径>
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="DETRAC 元数据提取")
    parser.add_argument(
        "--input_dir",
        required=True,
        help="DETRAC 数据集目录（包含 XML 标注）",
    )
    parser.add_argument(
        "--output_file",
        default="detrac_metadata.jsonl",
        help="输出 JSONL 文件路径",
    )
    return parser.parse_args()


def extract_frame_metadata(xml_path: str) -> List[Dict]:
    """
    从 DETRAC XML 提取每帧的交通元数据

    返回 JSONL 记录列表，每条记录包含一帧的统计信息。
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    records = []
    for frame_elem in root.findall("frame"):
        frame_num = int(frame_elem.get("number", 0))
        targets = []

        for target_elem in frame_elem.findall("target"):
            attr_elem = target_elem.find("attribute")
            if attr_elem is None:
                continue

            speed = float(attr_elem.get("speed", 0))
            vehicle_type = attr_elem.get("vehicle_type", "unknown")
            orientation = attr_elem.get("orientation", "unknown")
            trajectory = attr_elem.get("trajectory", "unknown")

            targets.append({
                "speed": speed,
                "vehicle_type": vehicle_type,
                "orientation": orientation,
                "trajectory": trajectory,
            })

        if not targets:
            continue

        # 统计帧级元数据
        vehicle_count = len(targets)
        avg_speed = sum(t["speed"] for t in targets) / vehicle_count if vehicle_count > 0 else 0

        # 按车型统计
        vehicle_types = {}
        for t in targets:
            vtype = t["vehicle_type"]
            vehicle_types[vtype] = vehicle_types.get(vtype, 0) + 1

        # 计算交通密度（归一化到 0-1，基于 DETRAC 常见场景）
        density = min(vehicle_count / 30.0, 1.0)

        records.append({
            "frame_id": f"{Path(xml_path).stem}_{frame_num:05d}",
            "timestamp": f"2026-01-01T00:{frame_num:02d}:00",  # 占位时间戳
            "vehicle_count": vehicle_count,
            "avg_speed": round(avg_speed, 2),
            "vehicle_types": vehicle_types,
            "density": round(density, 4),
            "vehicle_details": [
                {
                    "speed": t["speed"],
                    "vehicle_type": t["vehicle_type"],
                    "orientation": t["orientation"],
                    "trajectory": t["trajectory"],
                }
                for t in targets
            ],
        })

    return records


def main():
    """主流程：遍历 XML 文件 → 提取元数据 → 输出 JSONL"""
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file)

    if not input_dir.exists():
        print(f"错误：输入目录不存在: {input_dir}")
        return

    xml_files = list(input_dir.glob("*.xml"))
    if not xml_files:
        print(f"错误：在 {input_dir} 中未找到 XML 标注文件")
        return

    print(f"找到 {len(xml_files)} 个 XML 标注文件")

    total_records = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for xml_path in xml_files:
            records = extract_frame_metadata(str(xml_path))
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_records += 1

    print(f"元数据提取完成: 共 {total_records} 条记录，输出: {output_file}")


if __name__ == "__main__":
    main()