"""
COCO 格式转换脚本

功能:
    将 COCO JSON 标注数据集转换为 YOLO 格式，并自动划分数据集。

使用方式:
    python tools/convert_coco.py

处理流程:
    1. 读取 COCO JSON 文件
    2. 调用 DataConverter.coco_to_yolo() 转换标注
    3. 复制图像文件到输出目录
    4. 调用 DatasetSplitter.split_dataset() 划分数据集
    5. 生成 data.yaml

配置说明:
    使用前请修改脚本顶部的 COCO_JSON_FILE、RAW_IMAGE_DIR、OUTPUT_DIR 和 CLASS_MAPPING。
"""
import os
import sys
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径，确保能导入 app 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.training.data_converter import DataConverter
from app.training.dataset_splitter import DatasetSplitter

# ==================== 配置常量（请根据实际数据集修改）====================
COCO_JSON_FILE = os.path.join(PROJECT_ROOT, "datasets/your_scene/annotations/coco.json")
RAW_IMAGE_DIR = os.path.join(PROJECT_ROOT, "datasets/your_scene/images")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "datasets/your_scene/yolo_dataset")
# 用户自行配置类别映射，例如: {"airplane": 0, "car": 1}
CLASS_MAPPING = {}
# ======================================================================

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def main():
    print("=" * 60)
    print("开始 COCO 格式转换流程")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"COCO JSON 文件: {COCO_JSON_FILE}")
    print(f"原始图像目录: {RAW_IMAGE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    # ========== 步骤1: 读取 COCO JSON 文件 ==========
    print("\n[步骤1] 读取 COCO JSON 文件...")

    if not os.path.isfile(COCO_JSON_FILE):
        print(f"错误: COCO JSON 文件不存在: {COCO_JSON_FILE}")
        return 1

    # 读取 JSON 获取类别信息，用于自动推断 CLASS_MAPPING
    import json
    try:
        with open(COCO_JSON_FILE, "r", encoding="utf-8") as f:
            coco_data = json.load(f)
    except json.JSONDecodeError:
        print(f"错误: COCO JSON 文件解析失败: {COCO_JSON_FILE}")
        return 1

    categories = coco_data.get("categories", [])
    if not CLASS_MAPPING:
        # 自动按 categories 顺序生成 class_mapping
        class_mapping = {}
        for idx, cat in enumerate(categories):
            cname = cat.get("name", "").strip()
            if cname:
                class_mapping[cname] = idx
        if class_mapping:
            print(f"自动生成类别映射（共 {len(class_mapping)} 类）: {class_mapping}")
        else:
            print("错误: 无法从 COCO JSON 中提取类别信息，请手动配置 CLASS_MAPPING")
            return 1
    else:
        class_mapping = CLASS_MAPPING
        print(f"使用手动配置的类别映射: {class_mapping}")

    # 提取类别名称列表
    class_names = sorted(class_mapping.keys(), key=lambda k: class_mapping[k])
    print(f"类别列表: {class_names}")

    # ========== 步骤2: COCO → YOLO 转换 ==========
    print("\n[步骤2] 开始 COCO → YOLO 转换...")

    # 创建临时标注目录
    temp_label_dir = os.path.join(PROJECT_ROOT, "tmp/coco_yolo_labels")
    if os.path.exists(temp_label_dir):
        shutil.rmtree(temp_label_dir)
    os.makedirs(temp_label_dir, exist_ok=True)

    stats = DataConverter.coco_to_yolo(
        json_path=COCO_JSON_FILE,
        output_dir=temp_label_dir,
        class_mapping=class_mapping
    )

    print(f"转换完成:")
    print(f"  总计图像: {stats['total']}")
    print(f"  成功转换: {stats['converted']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")

    if stats['converted'] == 0:
        print("错误: 没有任何标注成功转换，终止流程")
        return 1

    # ========== 步骤3: 复制图像文件到临时目录 ==========
    print("\n[步骤3] 复制图像文件...")

    if not os.path.isdir(RAW_IMAGE_DIR):
        print(f"错误: 图像目录不存在: {RAW_IMAGE_DIR}")
        return 1

    temp_image_dir = os.path.join(PROJECT_ROOT, "tmp/coco_images")
    if os.path.exists(temp_image_dir):
        shutil.rmtree(temp_image_dir)
    os.makedirs(temp_image_dir, exist_ok=True)

    image_files = [
        p for p in Path(RAW_IMAGE_DIR).iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]

    if not image_files:
        print(f"错误: 图像目录中未找到支持的图像文件: {RAW_IMAGE_DIR}")
        return 1

    copy_count = 0
    for img_path in image_files:
        shutil.copy2(img_path, os.path.join(temp_image_dir, img_path.name))
        copy_count += 1

    print(f"已复制 {copy_count} 张图像到临时目录")

    # ========== 步骤4: 划分数据集 ==========
    print("\n[步骤4] 开始划分数据集（8:1:1）...")

    if os.path.exists(OUTPUT_DIR):
        print(f"输出目录已存在，正在清空: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    try:
        split_stats = DatasetSplitter.split_dataset(
            image_dir=temp_image_dir,
            label_dir=temp_label_dir,
            output_dir=OUTPUT_DIR,
            class_names=class_names,
            ratios=(0.8, 0.1, 0.1),
            seed=42
        )
        print(f"数据集划分完成:")
        print(f"  训练集: {split_stats['train']} 张")
        print(f"  验证集: {split_stats['val']} 张")
        print(f"  测试集: {split_stats['test']} 张")
        print(f"  总计: {split_stats['total']} 张")
    except Exception as e:
        print(f"数据集划分失败: {e}")
        return 1

    # ========== 步骤5: 生成 data.yaml 已在 split_dataset 中完成 ==========
    print(f"\n[步骤5] data.yaml 已生成: {os.path.join(OUTPUT_DIR, 'data.yaml')}")

    # ========== 清理临时目录 ==========
    print("\n清理临时目录...")
    if os.path.exists(temp_label_dir):
        shutil.rmtree(temp_label_dir)
    if os.path.exists(temp_image_dir):
        shutil.rmtree(temp_image_dir)
    print("临时目录已清理")

    # ========== 完成 ==========
    print("\n" + "=" * 60)
    print("COCO 格式转换流程完成！")
    print(f"最终数据集位置: {OUTPUT_DIR}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())