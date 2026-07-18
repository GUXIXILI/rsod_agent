"""
YOLO 标注修复脚本

功能:
    遍历 YOLO 格式标注文件，修复格式错误、裁剪越界坐标、删除无效行。

使用方式:
    python tools/fix_bbox.py [标注目录]

    默认标注目录: datasets/rsod/yolo_dataset/labels

修复规则:
    1. 检查每行格式是否正确（5个值，class_id 为整数，坐标为 0~1 浮点数）
    2. 裁剪越界坐标到 [0, 1] 区间
    3. 删除无效行（坐标全为0或class_id为负数等）
    4. 输出修复统计
"""
import os
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ==================== 配置常量 ====================
DEFAULT_LABEL_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset/labels")
# =================================================


def fix_bbox_file(txt_path: Path) -> dict:
    """
    修复单个 YOLO 标注文件。

    返回:
        {"fixed": True/False, "issues": [...], "original_lines": N, "kept_lines": N}
    """
    result = {
        "fixed": False,
        "issues": [],
        "original_lines": 0,
        "kept_lines": 0,
    }

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            original_lines = f.readlines()
    except Exception as e:
        result["issues"].append(f"无法读取文件: {e}")
        return result

    result["original_lines"] = len(original_lines)
    fixed_lines = []

    for line_no, line in enumerate(original_lines, 1):
        line = line.strip()
        if not line:
            # 保留空行
            fixed_lines.append("")
            continue

        parts = line.split()

        # 检查字段数
        if len(parts) != 5:
            result["issues"].append(f"第{line_no}行: 字段数不为5 ({len(parts)}个)，已删除")
            result["fixed"] = True
            continue

        # 解析 class_id
        try:
            class_id = int(parts[0])
        except ValueError:
            result["issues"].append(f"第{line_no}行: class_id 不是整数，已删除")
            result["fixed"] = True
            continue

        # 检查 class_id 是否为负数
        if class_id < 0:
            result["issues"].append(f"第{line_no}行: class_id 为负数 ({class_id})，已删除")
            result["fixed"] = True
            continue

        # 解析坐标
        try:
            coords = [float(x) for x in parts[1:5]]
        except ValueError:
            result["issues"].append(f"第{line_no}行: 坐标值不是数字，已删除")
            result["fixed"] = True
            continue

        x_center, y_center, w, h = coords

        # 检查退化框（宽或高为0）
        if w <= 0 and h <= 0:
            result["issues"].append(f"第{line_no}行: 退化框 (w={w:.6f}, h={h:.6f})，已删除")
            result["fixed"] = True
            continue

        # 裁剪越界坐标到 [0, 1]
        original = (x_center, y_center, w, h)
        x_center = max(0.0, min(1.0, x_center))
        y_center = max(0.0, min(1.0, y_center))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))

        if (x_center, y_center, w, h) != original:
            result["issues"].append(
                f"第{line_no}行: 坐标越界已裁剪 "
                f"({original[0]:.4f},{original[1]:.4f},{original[2]:.4f},{original[3]:.4f}) → "
                f"({x_center:.4f},{y_center:.4f},{w:.4f},{h:.4f})"
            )
            result["fixed"] = True

        # 确保裁剪后框仍然有效
        if w <= 0 or h <= 0:
            result["issues"].append(f"第{line_no}行: 裁剪后为退化框，已删除")
            result["fixed"] = True
            continue

        fixed_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

    result["kept_lines"] = len([l for l in fixed_lines if l.strip()])

    # 写回文件
    if result["fixed"]:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(fixed_lines) + "\n" if fixed_lines else "")

    return result


def main():
    # 支持命令行参数指定标注目录
    if len(sys.argv) > 1:
        label_dir = Path(sys.argv[1])
    else:
        label_dir = Path(DEFAULT_LABEL_DIR)

    print("=" * 60)
    print("YOLO 标注修复工具")
    print(f"标注目录: {label_dir}")
    print("=" * 60)

    if not label_dir.exists() or not label_dir.is_dir():
        print(f"错误: 标注目录不存在: {label_dir}")
        return 1

    # 收集所有 .txt 文件（递归查找子目录）
    txt_files = sorted(label_dir.rglob("*.txt"))

    if not txt_files:
        print(f"错误: 未找到任何 .txt 标注文件: {label_dir}")
        return 1

    print(f"找到 {len(txt_files)} 个标注文件，开始修复...")

    # 统计信息
    total_files = 0
    fixed_files = 0
    total_original_lines = 0
    total_kept_lines = 0
    total_issues = 0
    issue_summary = defaultdict(int)

    for txt_path in txt_files:
        total_files += 1
        result = fix_bbox_file(txt_path)
        total_original_lines += result["original_lines"]
        total_kept_lines += result["kept_lines"]

        if result["fixed"]:
            fixed_files += 1
            total_issues += len(result["issues"])

            # 显示有问题的文件详情
            relative_path = txt_path.relative_to(label_dir)
            print(f"\n  {relative_path}:")
            for issue in result["issues"][:5]:
                print(f"    - {issue}")
                # 统计问题类型
                if "字段数" in issue:
                    issue_summary["字段数错误"] += 1
                elif "class_id" in issue and "负数" in issue:
                    issue_summary["class_id负数"] += 1
                elif "class_id" in issue and "整数" in issue:
                    issue_summary["class_id非整数"] += 1
                elif "退化框" in issue:
                    issue_summary["退化框"] += 1
                elif "越界" in issue:
                    issue_summary["坐标越界"] += 1
                elif "数字" in issue:
                    issue_summary["坐标非数字"] += 1
                else:
                    issue_summary["其他"] += 1
            if len(result["issues"]) > 5:
                print(f"    ... 共 {len(result['issues'])} 个问题")

    # 汇总报告
    print("\n" + "=" * 60)
    print("修复统计")
    print("=" * 60)
    print(f"  扫描文件总数: {total_files}")
    print(f"  修复文件数: {fixed_files}")
    print(f"  正常文件数: {total_files - fixed_files}")
    print(f"  原始行数: {total_original_lines}")
    print(f"  保留行数: {total_kept_lines}")
    print(f"  删除行数: {total_original_lines - total_kept_lines}")
    print(f"  总问题数: {total_issues}")

    if issue_summary:
        print(f"\n  问题类型分布:")
        for issue_type, count in sorted(issue_summary.items(), key=lambda x: -x[1]):
            print(f"    {issue_type}: {count} 处")

    print("\n修复完成！")
    return 0


if __name__ == "__main__":
    exit(main())