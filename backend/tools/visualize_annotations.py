"""
数据标注可视化工具

功能:
    可视化 YOLO 格式数据集中的标注框，支持随机抽样、单张查看、网格概览图生成。

使用方式:
    # 随机抽样 10 张（默认）并弹窗查看
    python tools/visualize_annotations.py

    # 随机抽样 20 张，保存到指定目录
    python tools/visualize_annotations.py --count 20 --save-dir ./vis_output

    # 查看单张图像
    python tools/visualize_annotations.py --image datasets/rsod/yolo_dataset/images/train/aircraft_100.jpg

    # 生成网格概览图
    python tools/visualize_annotations.py --grid --count 16 --save-dir ./vis_output

    # 指定数据集和子集
    python tools/visualize_annotations.py --dataset datasets/rsod/yolo_dataset --subset val --count 5
"""
import os
import sys
import random
import argparse
import math
from pathlib import Path

import cv2
import numpy as np

# ==================== 配置常量 ====================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")
DEFAULT_SUBSET = "train"  # train/val/test
DEFAULT_COUNT = 10

# BGR 颜色列表，16 种颜色循环使用
COLORS = [
    (0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255),
    (255, 255, 0), (255, 0, 255), (0, 128, 255), (128, 0, 255),
    (255, 128, 0), (128, 255, 0), (0, 255, 128), (255, 0, 128),
    (128, 128, 255), (255, 128, 128), (128, 255, 128), (128, 128, 128),
]

# 支持的图像文件扩展名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
# =================================================


def parse_data_yaml(yaml_path):
    """
    纯文本解析 data.yaml，获取类别名称列表。

    参数：
        yaml_path: data.yaml 文件路径

    返回：
        cls_names: 类别名称列表，索引对应类别 ID
    """
    if not os.path.isfile(yaml_path):
        print(f"错误: data.yaml 不存在: {yaml_path}")
        return []

    with open(yaml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 解析 names 块：找到 "names:" 行，然后逐行读取 "  id: name" 格式
    cls_names = []
    in_names_block = False

    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")

        # 检测 names 块开始
        if stripped.strip() == "names:" or stripped.strip().startswith("names:"):
            in_names_block = True
            # 处理 "names: {0: aircraft, 1: oiltank}" 这种内联格式
            after_key = stripped.split(":", 1)[1].strip()
            if after_key:
                # 内联格式：移除花括号后解析
                after_key = after_key.strip("{}").strip()
                if after_key:
                    # 按逗号分割，但要注意花括号嵌套（names 通常不会嵌套）
                    pairs = after_key.split(",")
                    for pair in pairs:
                        pair = pair.strip()
                        if ":" in pair:
                            parts = pair.split(":", 1)
                            # 提取类别名，去除引号和空格
                            name = parts[1].strip().strip("'").strip('"').strip()
                            cls_names.append(name)
                    break  # 内联格式，无需继续读取
            continue

        if not in_names_block:
            continue

        # 在 names 块内，逐行读取 "  id: name" 格式
        # 检查是否已离开 names 块（遇到非缩进行且非空行）
        if stripped.strip() == "":
            continue

        # 如果遇到顶级键（无缩进），names 块结束
        if not stripped.startswith(" ") and ":" in stripped:
            break

        # 解析 "  id: name" 行
        if ":" in stripped:
            parts = stripped.split(":", 1)
            name = parts[1].strip().strip("'").strip('"').strip()
            cls_names.append(name)

    if not cls_names:
        print(f"警告: 未能从 data.yaml 中解析出类别名称")
    else:
        print(f"从 data.yaml 解析到 {len(cls_names)} 个类别: {cls_names}")

    return cls_names


def draw_bboxes(image, label_path, cls_names, colors):
    """
    在图像上绘制所有标注框。

    参数：
        image: OpenCV 图像 (numpy array)
        label_path: 标注文件路径 (.txt)
        cls_names: 类别名称列表
        colors: BGR 颜色列表

    返回：
        image: 绘制后的图像
    """
    if not os.path.isfile(label_path):
        return image

    with open(label_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    h, w = image.shape[:2]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 5:
            continue

        try:
            class_id = int(parts[0])
            x_center = float(parts[1]) * w
            y_center = float(parts[2]) * h
            box_w = float(parts[3]) * w
            box_h = float(parts[4]) * h
        except (ValueError, IndexError):
            continue

        # 转换为左上角和右下角像素坐标
        x1 = int(x_center - box_w / 2)
        y1 = int(y_center - box_h / 2)
        x2 = int(x_center + box_w / 2)
        y2 = int(y_center + box_h / 2)

        # 确保坐标在图像范围内
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w - 1, x2)
        y2 = min(h - 1, y2)

        if x2 <= x1 or y2 <= y1:
            continue

        # 获取颜色（循环使用）
        color = colors[class_id % len(colors)]

        # 获取类别名称
        label_text = cls_names[class_id] if class_id < len(cls_names) else f"cls_{class_id}"

        # 绘制标注框，线条宽度 2px
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        # 绘制类别标签（带背景填充）
        (text_w, text_h), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        # 标签绘制在框的左上角
        label_y1 = max(0, y1 - text_h - 4)
        label_x1 = x1
        label_x2 = x1 + text_w + 4
        label_y2 = y1

        # 背景填充
        cv2.rectangle(image, (label_x1, label_y1), (label_x2, label_y2), color, -1)
        # 白色文字
        cv2.putText(
            image, label_text, (label_x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )

    return image


def visualize_random(dataset_dir, subset, count, cls_names, colors, save_dir=None):
    """
    随机抽样可视化：从指定子集中随机抽取图像并绘制标注框。

    参数：
        dataset_dir: 数据集根目录
        subset: 子集名称 (train/val/test)
        count: 抽样数量
        cls_names: 类别名称列表
        colors: BGR 颜色列表
        save_dir: 保存目录（None 则弹窗显示）
    """
    img_dir = os.path.join(dataset_dir, "images", subset)
    lbl_dir = os.path.join(dataset_dir, "labels", subset)

    if not os.path.isdir(img_dir):
        print(f"错误: 图像目录不存在: {img_dir}")
        return

    # 收集所有图像文件
    image_files = sorted([
        p for p in Path(img_dir).iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ])

    if not image_files:
        print(f"错误: 目录中无图像文件: {img_dir}")
        return

    # 限制抽样数量
    actual_count = min(count, len(image_files))
    sampled = random.sample(image_files, actual_count)

    print(f"从 {subset} 集 ({len(image_files)} 张) 中随机抽样 {actual_count} 张")

    for img_path in sampled:
        label_name = img_path.stem + ".txt"
        label_path = os.path.join(lbl_dir, label_name)

        print(f"  处理: {img_path.name}")

        image = cv2.imread(str(img_path))
        if image is None:
            print(f"    警告: 无法读取图像 {img_path.name}")
            continue

        image = draw_bboxes(image, label_path, cls_names, colors)

        if save_dir:
            # 保存到文件
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"{subset}_{img_path.name}")
            cv2.imwrite(save_path, image)
            print(f"    已保存: {save_path}")
        else:
            # 弹窗查看
            cv2.imshow(f"Annotation - {img_path.name}", image)
            key = cv2.waitKey(0)
            cv2.destroyAllWindows()
            if key == 27:  # ESC 键退出
                print("  用户按 ESC 退出浏览")
                break

    if not save_dir:
        cv2.destroyAllWindows()


def visualize_single(image_path, label_dir, cls_names, colors, save_dir=None):
    """
    单张可视化：查看指定图像及其标注。

    参数：
        image_path: 图像文件路径
        label_dir: 标注文件所在目录
        cls_names: 类别名称列表
        colors: BGR 颜色列表
        save_dir: 保存目录（None 则弹窗显示）
    """
    if not os.path.isfile(image_path):
        print(f"错误: 图像文件不存在: {image_path}")
        return

    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图像: {image_path}")
        return

    # 推断标注文件路径
    stem = Path(image_path).stem
    label_path = os.path.join(label_dir, stem + ".txt")

    print(f"查看单张图像: {os.path.basename(image_path)}")
    if os.path.isfile(label_path):
        print(f"  标注文件: {label_path}")
    else:
        print(f"  警告: 未找到标注文件 {label_path}")

    image = draw_bboxes(image, label_path, cls_names, colors)

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"single_{os.path.basename(image_path)}")
        cv2.imwrite(save_path, image)
        print(f"  已保存: {save_path}")
    else:
        cv2.imshow(f"Annotation - {os.path.basename(image_path)}", image)
        print("  按任意键关闭窗口...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def visualize_grid(dataset_dir, subset, count, cls_names, colors, save_dir=None):
    """
    生成网格概览图：将多张标注图像拼接为一张网格图。

    参数：
        dataset_dir: 数据集根目录
        subset: 子集名称 (train/val/test)
        count: 抽样数量
        cls_names: 类别名称列表
        colors: BGR 颜色列表
        save_dir: 保存目录（None 则弹窗显示）
    """
    img_dir = os.path.join(dataset_dir, "images", subset)
    lbl_dir = os.path.join(dataset_dir, "labels", subset)

    if not os.path.isdir(img_dir):
        print(f"错误: 图像目录不存在: {img_dir}")
        return

    # 收集所有图像文件
    image_files = sorted([
        p for p in Path(img_dir).iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ])

    if not image_files:
        print(f"错误: 目录中无图像文件: {img_dir}")
        return

    actual_count = min(count, len(image_files))
    sampled = random.sample(image_files, actual_count)

    print(f"生成网格概览图: {subset} 集, {actual_count} 张图像")

    # 读取并绘制所有图像
    annotated_images = []
    for img_path in sampled:
        label_name = img_path.stem + ".txt"
        label_path = os.path.join(lbl_dir, label_name)

        print(f"  处理: {img_path.name}")
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"    警告: 无法读取图像 {img_path.name}")
            continue

        image = draw_bboxes(image, label_path, cls_names, colors)
        annotated_images.append(image)

    if not annotated_images:
        print("错误: 没有成功读取任何图像")
        return

    # 尝试使用 matplotlib 生成网格图
    try:
        import matplotlib.pyplot as plt
        _grid_with_matplotlib(annotated_images, cls_names, colors, subset, save_dir)
    except ImportError:
        print("matplotlib 不可用，使用 OpenCV 拼接方式生成网格图")
        _grid_with_cv2(annotated_images, subset, save_dir)


def _grid_with_matplotlib(images, cls_names, colors, subset, save_dir):
    """使用 matplotlib 生成网格图（RGB 色彩空间）"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    n = len(images)
    # 计算网格行列数，尽量接近正方形
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3))
    axes = np.array(axes).flatten() if n > 1 else [axes]

    for i, img in enumerate(images):
        ax = axes[i]
        # BGR -> RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)
        ax.set_title(f"Image {i + 1}", fontsize=8)
        ax.axis("off")

    # 隐藏多余的子图
    for i in range(n, len(axes)):
        axes[i].axis("off")

    # 添加图例
    legend_patches = []
    for cid, name in enumerate(cls_names):
        color_bgr = colors[cid % len(colors)]
        # BGR -> RGB 颜色转换
        color_rgb = tuple(c / 255.0 for c in reversed(color_bgr))
        legend_patches.append(mpatches.Patch(color=color_rgb, label=name))
    fig.legend(handles=legend_patches, loc="lower center", ncol=len(cls_names), fontsize=8)

    plt.suptitle(f"Dataset: {subset} - {n} images with annotations", fontsize=14)
    plt.tight_layout(rect=[0, 0.05, 1, 0.97])

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"grid_{subset}_{n}.png")
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"网格概览图已保存: {save_path}")
    else:
        plt.show()

    plt.close()


def _grid_with_cv2(images, subset, save_dir):
    """使用 OpenCV 拼接生成网格图（BGR 色彩空间，无图例）"""
    n = len(images)
    # 统一缩放到固定大小
    max_h = max(img.shape[0] for img in images)
    max_w = max(img.shape[1] for img in images)

    # 限制单张图像最大尺寸，避免拼接后过大
    target_size = 300
    scale = min(target_size / max_h, target_size / max_w, 1.0)

    resized = []
    for img in images:
        new_w = int(img.shape[1] * scale)
        new_h = int(img.shape[0] * scale)
        resized_img = cv2.resize(img, (new_w, new_h))
        # 填充到统一尺寸
        padded = np.zeros((target_size, target_size, 3), dtype=np.uint8)
        padded[:new_h, :new_w] = resized_img
        resized.append(padded)

    # 计算网格行列数
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))

    # 拼接行
    row_images = []
    for r in range(rows):
        row_slice = resized[r * cols:(r + 1) * cols]
        # 不足一行时用黑色填充
        while len(row_slice) < cols:
            row_slice.append(np.zeros((target_size, target_size, 3), dtype=np.uint8))
        row_images.append(np.hstack(row_slice))

    grid = np.vstack(row_images)

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"grid_{subset}_{n}.jpg")
        cv2.imwrite(save_path, grid)
        print(f"网格概览图已保存: {save_path}")
    else:
        cv2.imshow(f"Grid - {subset} ({n} images)", grid)
        print("按任意键关闭窗口...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def find_label_dir_for_image(image_path, dataset_dir):
    """
    根据图像路径推断标注目录。

    参数：
        image_path: 图像文件路径
        dataset_dir: 数据集根目录

    返回：
        label_dir: 标注文件所在目录
    """
    img_path = Path(image_path).resolve()
    ds_path = Path(dataset_dir).resolve()

    # 尝试匹配 images/{subset}/ 结构
    try:
        rel = img_path.relative_to(ds_path / "images")
        subset = rel.parts[0] if rel.parts else ""
        label_dir = str(ds_path / "labels" / subset)
        return label_dir
    except ValueError:
        pass

    # 回退：假设 labels 与 images 同级
    label_dir = str(img_path.parent.parent / "labels" / img_path.parent.name)
    return label_dir


def main():
    parser = argparse.ArgumentParser(
        description="YOLO 格式数据标注可视化工具"
    )
    parser.add_argument(
        "--dataset", type=str, default=DEFAULT_DATASET_DIR,
        help=f"数据集根目录（默认: {DEFAULT_DATASET_DIR}）"
    )
    parser.add_argument(
        "--subset", type=str, default=DEFAULT_SUBSET,
        help=f"子集名称: train/val/test（默认: {DEFAULT_SUBSET}）"
    )
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT,
        help=f"随机抽样数量（默认: {DEFAULT_COUNT}）"
    )
    parser.add_argument(
        "--image", type=str, default=None,
        help="指定单张图像路径进行查看"
    )
    parser.add_argument(
        "--grid", action="store_true",
        help="生成网格概览图"
    )
    parser.add_argument(
        "--save-dir", type=str, default=None,
        help="保存目录（不指定则弹窗显示）"
    )

    args = parser.parse_args()

    # 解析 data.yaml 获取类别名称
    yaml_path = os.path.join(args.dataset, "data.yaml")
    print(f"读取 data.yaml: {yaml_path}")
    cls_names = parse_data_yaml(yaml_path)

    if not cls_names:
        print("错误: 未能解析类别名称，请检查 data.yaml 文件")
        return 1

    # 存图目录
    save_dir = args.save_dir

    if args.image:
        # 单张查看模式
        label_dir = find_label_dir_for_image(args.image, args.dataset)
        visualize_single(args.image, label_dir, cls_names, COLORS, save_dir)
    elif args.grid:
        # 网格概览图模式
        visualize_grid(args.dataset, args.subset, args.count, cls_names, COLORS, save_dir)
    else:
        # 默认：随机抽样模式
        visualize_random(args.dataset, args.subset, args.count, cls_names, COLORS, save_dir)

    print("完成。")
    return 0


if __name__ == "__main__":
    exit(main())