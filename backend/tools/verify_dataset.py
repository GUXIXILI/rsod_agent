"""
数据集验证脚本

功能:
    验证 YOLO 格式数据集的完整性和合规性，输出详细的验证报告。

使用方式:
    python tools/verify_dataset.py [数据集目录]

    默认数据集目录: datasets/rsod/yolo_dataset

验证项目:
    1. 目录结构完整性（images/train|val|test, labels/train|val|test 目录是否存在）
    2. 图像-标注文件配对检查（每张图是否有对应标注）
    3. YOLO 格式合规性（归一化坐标是否在 0~1 范围，每行是否有 5 个值）
    4. 类别分布统计（每个类别有多少标注框）
    5. 空标注文件检测（哪些图像没有目标）
    6. data.yaml 配置验证（nc、names 是否与标注实际类别一致）
"""
import os
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ==================== 配置常量 ====================
DEFAULT_DATASET_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")
# =================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def verify_directory_structure(dataset_dir: Path) -> dict:
    """验证目录结构完整性"""
    print("\n" + "=" * 60)
    print("[验证1] 目录结构完整性检查")
    print("=" * 60)

    subsets = ["train", "val", "test"]
    results = {"ok": True, "details": []}

    for subset in subsets:
        img_dir = dataset_dir / "images" / subset
        lbl_dir = dataset_dir / "labels" / subset

        img_exists = img_dir.is_dir()
        lbl_exists = lbl_dir.is_dir()

        status = "✓" if (img_exists and lbl_exists) else "✗"
        results["details"].append({
            "subset": subset,
            "images": img_exists,
            "labels": lbl_exists,
            "status": img_exists and lbl_exists
        })

        if not img_exists:
            print(f"  {status} images/{subset}/ 目录不存在")
            results["ok"] = False
        if not lbl_exists:
            print(f"  {status} labels/{subset}/ 目录不存在")
            results["ok"] = False
        if img_exists and lbl_exists:
            print(f"  {status} images/{subset}/ 和 labels/{subset}/ 目录存在")

    # 检查 data.yaml
    yaml_path = dataset_dir / "data.yaml"
    yaml_exists = yaml_path.is_file()
    if yaml_exists:
        print(f"  ✓ data.yaml 文件存在")
    else:
        print(f"  ✗ data.yaml 文件不存在")
        results["ok"] = False
    results["yaml_exists"] = yaml_exists

    if results["ok"]:
        print("  结果: 通过")
    else:
        print("  结果: 存在问题")
    return results


def verify_image_label_pairs(dataset_dir: Path) -> dict:
    """检查图像-标注文件配对"""
    print("\n" + "=" * 60)
    print("[验证2] 图像-标注文件配对检查")
    print("=" * 60)

    results = {"ok": True, "details": {}}

    for subset in ["train", "val", "test"]:
        img_dir = dataset_dir / "images" / subset
        lbl_dir = dataset_dir / "labels" / subset

        if not img_dir.is_dir() or not lbl_dir.is_dir():
            continue

        image_files = [
            p for p in img_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        ]
        label_files = list(lbl_dir.glob("*.txt"))

        image_stems = {p.stem for p in image_files}
        label_stems = {p.stem for p in label_files}

        # 图像无标注
        images_without_labels = image_stems - label_stems
        # 标注无图像
        labels_without_images = label_stems - image_stems
        # 匹配的
        matched = image_stems & label_stems

        results["details"][subset] = {
            "total_images": len(image_files),
            "total_labels": len(label_files),
            "matched": len(matched),
            "images_without_labels": sorted(images_without_labels),
            "labels_without_images": sorted(labels_without_images),
        }

        print(f"  [{subset}] 图像: {len(image_files)} 张, 标注: {len(label_files)} 个, 匹配: {len(matched)} 对")

        if images_without_labels:
            print(f"    警告: {len(images_without_labels)} 张图像无对应标注:")
            for stem in sorted(images_without_labels)[:5]:
                print(f"      - {stem}")
            if len(images_without_labels) > 5:
                print(f"      ... 共 {len(images_without_labels)} 个")
            results["ok"] = False

        if labels_without_images:
            print(f"    警告: {len(labels_without_images)} 个标注无对应图像:")
            for stem in sorted(labels_without_images)[:5]:
                print(f"      - {stem}")
            if len(labels_without_images) > 5:
                print(f"      ... 共 {len(labels_without_images)} 个")
            results["ok"] = False

    if results["ok"]:
        print("  结果: 通过")
    else:
        print("  结果: 存在问题")
    return results


def verify_yolo_format(dataset_dir: Path) -> dict:
    """验证 YOLO 格式合规性"""
    print("\n" + "=" * 60)
    print("[验证3] YOLO 格式合规性检查")
    print("=" * 60)

    results = {"ok": True, "invalid_files": [], "total_files": 0, "total_lines": 0}

    for subset in ["train", "val", "test"]:
        lbl_dir = dataset_dir / "labels" / subset
        if not lbl_dir.is_dir():
            continue

        for txt_path in sorted(lbl_dir.glob("*.txt")):
            results["total_files"] += 1
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"  ✗ 无法读取: {txt_path.name} ({e})")
                results["invalid_files"].append({"file": txt_path.name, "error": str(e)})
                results["ok"] = False
                continue

            for line_no, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                results["total_lines"] += 1
                parts = line.split()

                # 检查每行是否有 5 个值
                if len(parts) != 5:
                    results["invalid_files"].append({
                        "file": txt_path.name,
                        "line": line_no,
                        "error": f"字段数不为5: {len(parts)}"
                    })
                    results["ok"] = False
                    continue

                try:
                    class_id = int(parts[0])
                    coords = [float(x) for x in parts[1:5]]
                except ValueError:
                    results["invalid_files"].append({
                        "file": txt_path.name,
                        "line": line_no,
                        "error": "字段格式错误（非数字）"
                    })
                    results["ok"] = False
                    continue

                # 检查 class_id 是否为非负整数
                if class_id < 0:
                    results["invalid_files"].append({
                        "file": txt_path.name,
                        "line": line_no,
                        "error": f"class_id 为负数: {class_id}"
                    })
                    results["ok"] = False

                # 检查坐标是否在 [0, 1] 范围
                x_center, y_center, w, h = coords
                for name, val in [("x_center", x_center), ("y_center", y_center), ("w", w), ("h", h)]:
                    if val < -0.001 or val > 1.001:
                        results["invalid_files"].append({
                            "file": txt_path.name,
                            "line": line_no,
                            "error": f"{name} 越界: {val:.6f}"
                        })
                        results["ok"] = False
                        break
                else:
                    # 检查退化框
                    if w <= 0 or h <= 0:
                        results["invalid_files"].append({
                            "file": txt_path.name,
                            "line": line_no,
                            "error": f"退化框: w={w:.6f}, h={h:.6f}"
                        })
                        results["ok"] = False

    # 输出违规详情
    if results["invalid_files"]:
        print(f"  发现 {len(results['invalid_files'])} 个格式问题:")
        # 按文件分组显示
        file_issues = defaultdict(list)
        for item in results["invalid_files"]:
            file_issues[item["file"]].append(item)

        for fname, issues in sorted(file_issues.items()):
            print(f"    {fname}:")
            for issue in issues[:3]:
                if "line" in issue:
                    print(f"      第{issue['line']}行: {issue['error']}")
                else:
                    print(f"      {issue['error']}")
            if len(issues) > 3:
                print(f"      ... 共 {len(issues)} 个问题")

    print(f"  检查了 {results['total_files']} 个标注文件，共 {results['total_lines']} 个边界框")

    if results["ok"]:
        print("  结果: 通过")
    else:
        print("  结果: 存在问题")
    return results


def verify_class_distribution(dataset_dir: Path) -> dict:
    """类别分布统计"""
    print("\n" + "=" * 60)
    print("[验证4] 类别分布统计")
    print("=" * 60)

    class_counts = defaultdict(int)
    empty_files = []
    total_files = 0
    total_boxes = 0

    for subset in ["train", "val", "test"]:
        lbl_dir = dataset_dir / "labels" / subset
        if not lbl_dir.is_dir():
            continue

        subset_counts = defaultdict(int)
        subset_empty = []

        for txt_path in sorted(lbl_dir.glob("*.txt")):
            total_files += 1
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue

            if not lines or all(not line.strip() for line in lines):
                subset_empty.append(f"{subset}/{txt_path.name}")
                continue

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 1:
                    try:
                        class_id = int(parts[0])
                        class_counts[class_id] += 1
                        subset_counts[class_id] += 1
                        total_boxes += 1
                    except ValueError:
                        pass

        # 输出子集分布
        if subset_counts:
            print(f"  [{subset}] 标注框分布:")
            for cid in sorted(subset_counts.keys()):
                print(f"    类别 {cid}: {subset_counts[cid]} 个框")
        else:
            print(f"  [{subset}] 无标注框")

        if subset_empty:
            empty_files.extend(subset_empty)

    # 汇总统计
    print(f"\n  汇总统计:")
    print(f"  总标注文件数: {total_files}")
    print(f"  总边界框数: {total_boxes}")
    if class_counts:
        print(f"  类别分布:")
        for cid in sorted(class_counts.keys()):
            pct = class_counts[cid] / total_boxes * 100 if total_boxes > 0 else 0
            print(f"    类别 {cid}: {class_counts[cid]} 个框 ({pct:.1f}%)")
    else:
        print("  未检测到任何边界框")

    return {"class_counts": dict(class_counts), "empty_files": empty_files, "total_files": total_files, "total_boxes": total_boxes}


def verify_empty_labels(dataset_dir: Path, empty_files: list):
    """空标注文件检测"""
    print("\n" + "=" * 60)
    print("[验证5] 空标注文件检测")
    print("=" * 60)

    if empty_files:
        print(f"  发现 {len(empty_files)} 个空标注文件（无目标的图像）:")
        for fname in empty_files[:20]:
            print(f"    - {fname}")
        if len(empty_files) > 20:
            print(f"    ... 共 {len(empty_files)} 个")
    else:
        print("  未发现空标注文件")

    print(f"  空标注文件总数: {len(empty_files)}")


def verify_data_yaml(dataset_dir: Path, class_counts: dict) -> dict:
    """验证 data.yaml 配置"""
    print("\n" + "=" * 60)
    print("[验证6] data.yaml 配置验证")
    print("=" * 60)

    yaml_path = dataset_dir / "data.yaml"
    results = {"ok": True}

    if not yaml_path.is_file():
        print("  ✗ data.yaml 文件不存在")
        results["ok"] = False
        return results

    import yaml
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  ✗ data.yaml 解析失败: {e}")
        results["ok"] = False
        return results

    # 检查 nc
    yaml_nc = data.get("nc")
    actual_nc = len(class_counts)
    if yaml_nc is not None:
        if yaml_nc == actual_nc:
            print(f"  ✓ nc = {yaml_nc}（与实际类别数一致）")
        else:
            print(f"  ✗ nc = {yaml_nc}，但实际标注中有 {actual_nc} 个类别")
            results["ok"] = False
    else:
        print(f"  ✗ data.yaml 中缺少 nc 字段")
        results["ok"] = False

    # 检查 names
    yaml_names = data.get("names")
    if yaml_names is not None:
        actual_class_ids = set(class_counts.keys())
        if isinstance(yaml_names, dict):
            yaml_class_ids = set(yaml_names.keys())
            if yaml_class_ids == actual_class_ids:
                print(f"  ✓ names 与实际类别一致: {yaml_names}")
            else:
                missing_in_yaml = actual_class_ids - yaml_class_ids
                extra_in_yaml = yaml_class_ids - actual_class_ids
                if missing_in_yaml:
                    print(f"  ✗ data.yaml 缺少类别: {missing_in_yaml}")
                if extra_in_yaml:
                    print(f"  ✗ data.yaml 多余类别: {extra_in_yaml}")
                results["ok"] = False
        elif isinstance(yaml_names, list):
            print(f"  ✓ names 格式为列表: {yaml_names}")
            if len(yaml_names) != actual_nc:
                print(f"  ✗ names 列表长度 ({len(yaml_names)}) 与 nc 不一致")
                results["ok"] = False
        else:
            print(f"  ✗ names 格式异常: {type(yaml_names)}")
            results["ok"] = False
    else:
        print(f"  ✗ data.yaml 中缺少 names 字段")
        results["ok"] = False

    # 检查路径
    for key in ["train", "val", "test"]:
        path_val = data.get(key)
        if path_val:
            print(f"  ✓ {key} = {path_val}")
        else:
            print(f"  ✗ 缺少 {key} 路径配置")
            results["ok"] = False

    if results["ok"]:
        print("  结果: 通过")
    else:
        print("  结果: 存在问题")
    return results


def main():
    # 支持命令行参数指定数据集目录
    if len(sys.argv) > 1:
        dataset_dir = Path(sys.argv[1])
    else:
        dataset_dir = Path(DEFAULT_DATASET_DIR)

    print("=" * 60)
    print("数据集验证工具")
    print(f"数据集目录: {dataset_dir}")
    print("=" * 60)

    if not dataset_dir.exists():
        print(f"错误: 数据集目录不存在: {dataset_dir}")
        return 1

    # 执行各项验证
    struct_result = verify_directory_structure(dataset_dir)
    pair_result = verify_image_label_pairs(dataset_dir)
    format_result = verify_yolo_format(dataset_dir)
    class_result = verify_class_distribution(dataset_dir)
    verify_empty_labels(dataset_dir, class_result["empty_files"])
    yaml_result = verify_data_yaml(dataset_dir, class_result["class_counts"])

    # 汇总报告
    print("\n" + "=" * 60)
    print("验证汇总")
    print("=" * 60)

    all_checks = [
        ("目录结构完整性", struct_result["ok"]),
        ("图像-标注配对", pair_result["ok"]),
        ("YOLO 格式合规性", format_result["ok"]),
        ("data.yaml 配置", yaml_result["ok"]),
    ]

    for name, ok in all_checks:
        status = "✓ 通过" if ok else "✗ 存在问题"
        print(f"  [{status}] {name}")

    total_ok = sum(1 for _, ok in all_checks if ok)
    print(f"\n总计: {total_ok}/{len(all_checks)} 项通过")

    if total_ok == len(all_checks):
        print("\n数据集验证全部通过！")
        return 0
    else:
        print("\n数据集存在问题，请根据上述报告修复。")
        return 1


if __name__ == "__main__":
    exit(main())