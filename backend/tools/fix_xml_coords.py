"""
VOC XML 标注修复脚本

功能:
    遍历 VOC XML 标注文件，修复边界框坐标问题。

使用方式:
    python tools/fix_xml_coords.py [XML目录]

    默认XML目录: datasets/rsod/raw/annotations

修复规则:
    1. 检查 bndbox 坐标是否在图像尺寸范围内，裁剪越界坐标
    2. 修复 xmin > xmax 或 ymin > ymax 的情况
    3. 输出修复统计
"""
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ==================== 配置常量 ====================
DEFAULT_XML_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/raw/annotations")
# =================================================


def fix_xml_file(xml_path: Path) -> dict:
    """
    修复单个 VOC XML 标注文件。

    返回:
        {"fixed": True/False, "issues": [...], "objects": N}
    """
    result = {
        "fixed": False,
        "issues": [],
        "objects": 0,
    }

    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
    except ET.ParseError:
        result["issues"].append(f"XML 解析失败，文件可能损坏")
        return result
    except Exception as e:
        result["issues"].append(f"无法读取文件: {e}")
        return result

    # 获取图像尺寸
    size_elem = root.find("size")
    if size_elem is None:
        result["issues"].append("缺少 <size> 元素，无法修复")
        return result

    width_elem = size_elem.find("width")
    height_elem = size_elem.find("height")

    if width_elem is None or height_elem is None:
        result["issues"].append("缺少 <width> 或 <height> 子元素，无法修复")
        return result

    try:
        img_width = float(width_elem.text)
        img_height = float(height_elem.text)
    except (ValueError, TypeError):
        result["issues"].append("图像尺寸无效")
        return result

    if img_width <= 0 or img_height <= 0:
        result["issues"].append(f"图像尺寸无效 (width={img_width}, height={img_height})")
        return result

    # 遍历所有 object 元素
    objects = root.findall("object")
    result["objects"] = len(objects)

    for obj_idx, obj in enumerate(objects):
        bndbox = obj.find("bndbox")
        if bndbox is None:
            result["issues"].append(f"第{obj_idx + 1}个object: 缺少 <bndbox>")
            result["fixed"] = True
            continue

        # 获取四个坐标元素
        xmin_elem = bndbox.find("xmin")
        ymin_elem = bndbox.find("ymin")
        xmax_elem = bndbox.find("xmax")
        ymax_elem = bndbox.find("ymax")

        if any(e is None for e in (xmin_elem, ymin_elem, xmax_elem, ymax_elem)):
            result["issues"].append(f"第{obj_idx + 1}个object: bndbox 坐标不完整")
            result["fixed"] = True
            continue

        try:
            xmin = float(xmin_elem.text)
            ymin = float(ymin_elem.text)
            xmax = float(xmax_elem.text)
            ymax = float(ymax_elem.text)
        except (ValueError, TypeError):
            result["issues"].append(f"第{obj_idx + 1}个object: 坐标值无效")
            result["fixed"] = True
            continue

        original = (xmin, ymin, xmax, ymax)
        changed = False

        # 修复 xmin > xmax
        if xmin > xmax:
            xmin, xmax = xmax, xmin
            result["issues"].append(
                f"第{obj_idx + 1}个object: xmin > xmax，已交换 "
                f"({original[0]:.0f}, {original[2]:.0f}) → ({xmin:.0f}, {xmax:.0f})"
            )
            changed = True

        # 修复 ymin > ymax
        if ymin > ymax:
            ymin, ymax = ymax, ymin
            result["issues"].append(
                f"第{obj_idx + 1}个object: ymin > ymax，已交换 "
                f"({original[1]:.0f}, {original[3]:.0f}) → ({ymin:.0f}, {ymax:.0f})"
            )
            changed = True

        # 裁剪越界坐标到 [0, img_width/img_height]
        if xmin < 0:
            result["issues"].append(f"第{obj_idx + 1}个object: xmin 越界 ({xmin:.0f} < 0)，已裁剪为 0")
            xmin = 0
            changed = True
        if ymin < 0:
            result["issues"].append(f"第{obj_idx + 1}个object: ymin 越界 ({ymin:.0f} < 0)，已裁剪为 0")
            ymin = 0
            changed = True
        if xmax > img_width:
            result["issues"].append(
                f"第{obj_idx + 1}个object: xmax 越界 ({xmax:.0f} > {img_width:.0f})，已裁剪为 {img_width:.0f}"
            )
            xmax = img_width
            changed = True
        if ymax > img_height:
            result["issues"].append(
                f"第{obj_idx + 1}个object: ymax 越界 ({ymax:.0f} > {img_height:.0f})，已裁剪为 {img_height:.0f}"
            )
            ymax = img_height
            changed = True

        if changed:
            result["fixed"] = True
            # 写回修改后的值
            xmin_elem.text = str(int(xmin))
            ymin_elem.text = str(int(ymin))
            xmax_elem.text = str(int(xmax))
            ymax_elem.text = str(int(ymax))

    # 如果有修改，写回文件
    if result["fixed"]:
        try:
            # 使用 minidom 格式化输出，保持 XML 可读性
            import xml.dom.minidom as minidom
            rough_string = ET.tostring(root, encoding="utf-8")
            reparsed = minidom.parseString(rough_string)
            pretty = reparsed.toprettyxml(indent="  ", encoding="utf-8")
            with open(xml_path, "wb") as f:
                f.write(pretty)
        except Exception as e:
            result["issues"].append(f"写回文件失败: {e}")

    return result


def main():
    # 支持命令行参数指定 XML 目录
    if len(sys.argv) > 1:
        xml_dir = Path(sys.argv[1])
    else:
        xml_dir = Path(DEFAULT_XML_DIR)

    print("=" * 60)
    print("VOC XML 标注修复工具")
    print(f"XML 目录: {xml_dir}")
    print("=" * 60)

    if not xml_dir.exists() or not xml_dir.is_dir():
        print(f"错误: XML 目录不存在: {xml_dir}")
        return 1

    # 收集所有 .xml 文件
    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        print(f"错误: 未找到任何 .xml 标注文件: {xml_dir}")
        return 1

    print(f"找到 {len(xml_files)} 个 XML 文件，开始修复...")

    # 统计信息
    total_files = 0
    fixed_files = 0
    total_objects = 0
    total_issues = 0
    issue_summary = defaultdict(int)

    for xml_path in xml_files:
        total_files += 1
        result = fix_xml_file(xml_path)
        total_objects += result["objects"]

        if result["fixed"]:
            fixed_files += 1
            total_issues += len(result["issues"])

            print(f"\n  {xml_path.name}:")
            for issue in result["issues"][:5]:
                print(f"    - {issue}")
                # 统计问题类型
                if "xmin > xmax" in issue:
                    issue_summary["xmin > xmax"] += 1
                elif "ymin > ymax" in issue:
                    issue_summary["ymin > ymax"] += 1
                elif "越界" in issue:
                    issue_summary["坐标越界"] += 1
                elif "不完整" in issue:
                    issue_summary["坐标不完整"] += 1
                elif "无效" in issue:
                    issue_summary["坐标值无效"] += 1
                elif "缺少" in issue:
                    issue_summary["缺少元素"] += 1
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
    print(f"  总 object 数: {total_objects}")
    print(f"  总问题数: {total_issues}")

    if issue_summary:
        print(f"\n  问题类型分布:")
        for issue_type, count in sorted(issue_summary.items(), key=lambda x: -x[1]):
            print(f"    {issue_type}: {count} 处")

    print("\n修复完成！")
    return 0


if __name__ == "__main__":
    exit(main())