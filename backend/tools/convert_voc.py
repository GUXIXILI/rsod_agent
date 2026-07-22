"""
VOC 格式转换主脚本

功能:
    将 RSOD 数据集的 VOC XML 标注完整转换为 YOLO 格式，并自动划分数据集。

使用方式:
    python tools/convert_voc.py

处理流程:
    1. 检查图片与XML匹配度（删除不匹配的文件）
    2. VOC→YOLO 转换
    3. 按 8:1:1 划分数据集
    4. 生成 data.yaml
    5. 清理临时目录

配置说明:
    配置常量已在脚本顶部硬编码，根据 RSOD 数据集预设。
    如需修改路径，请直接编辑脚本顶部的常量定义。
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

# ==================== 配置常量 ====================
RAW_IMAGE_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/raw/images")
RAW_ANNOTATION_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/raw/annotations")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")
CLASS_NAMES = ["aircraft", "oiltank", "overpass", "playground"]
CLASS_MAPPING = {name: idx for idx, name in enumerate(CLASS_NAMES)}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
# ===================================================

def main():
    print("=" * 60)
    print("开始 VOC 格式转换流程")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"原始图像目录: {RAW_IMAGE_DIR}")
    print(f"原始标注目录: {RAW_ANNOTATION_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    # ========== 步骤1: 检查图片与XML匹配度 ==========
    print("\n[步骤1] 检查图片与XML匹配度...")

    raw_image_path = Path(RAW_IMAGE_DIR)
    raw_anno_path = Path(RAW_ANNOTATION_DIR)

    if not raw_image_path.exists() or not raw_image_path.is_dir():
        print(f"错误: 图像目录不存在: {RAW_IMAGE_DIR}")
        return 1

    if not raw_anno_path.exists() or not raw_anno_path.is_dir():
        print(f"错误: 标注目录不存在: {RAW_ANNOTATION_DIR}")
        return 1

    # 获取所有图像和XML文件
    image_files = [p for p in raw_image_path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    xml_files = list(raw_anno_path.glob("*.xml"))

    print(f"找到 {len(image_files)} 张图像，{len(xml_files)} 个XML标注文件")

    # 建立 stem 集合
    image_stems = {p.stem for p in image_files}
    xml_stems = {p.stem for p in xml_files}

    # 删除不匹配的XML文件
    xml_to_delete = [p for p in xml_files if p.stem not in image_stems]
    if xml_to_delete:
        print(f"发现 {len(xml_to_delete)} 个XML没有对应图像，正在删除...")
        for p in xml_to_delete:
            p.unlink()
    else:
        print("所有XML都有对应图像")

    # 检查图像是否都有对应XML（只报告不删除）
    images_without_xml = [p for p in image_files if p.stem not in xml_stems]
    if images_without_xml:
        print(f"警告: 发现 {len(images_without_xml)} 张图像没有对应XML标注:")
        for p in images_without_xml[:10]:
            print(f"  - {p.name}")
        if len(images_without_xml) > 10:
            print(f"  ... 共 {len(images_without_xml)} 个")
    else:
        print("所有图像都有对应XML标注")

    print(f"匹配检查完成，剩余 {len([p for p in xml_files if p.stem in image_stems])} 个匹配对")

    # ========== 步骤2: VOC→YOLO 转换 ==========
    print("\n[步骤2] 开始 VOC → YOLO 转换...")

    # 创建临时转换目录
    temp_label_dir = os.path.join(PROJECT_ROOT, "tmp/yolo_labels")
    if os.path.exists(temp_label_dir):
        shutil.rmtree(temp_label_dir)
    os.makedirs(temp_label_dir, exist_ok=True)

    # 调用 DataConverter 进行转换
    stats = DataConverter.voc_to_yolo(
        xml_dir=RAW_ANNOTATION_DIR,
        output_dir=temp_label_dir,
        class_mapping=CLASS_MAPPING
    )

    print(f"转换完成:")
    print(f"  总计XML: {stats['total']}")
    print(f"  成功转换: {stats['converted']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")

    if stats['converted'] == 0:
        print("错误: 没有任何标注成功转换，终止流程")
        return 1

    # ========== 步骤3: 按 8:1:1 划分数据集 ==========
    print("\n[步骤3] 开始划分数据集（8:1:1）...")

    # 如果输出目录已存在，先清空
    if os.path.exists(OUTPUT_DIR):
        print(f"输出目录已存在，正在清空: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    # 调用 DatasetSplitter 进行划分
    try:
        split_stats = DatasetSplitter.split_dataset(
            image_dir=RAW_IMAGE_DIR,
            label_dir=temp_label_dir,
            output_dir=OUTPUT_DIR,
            class_names=CLASS_NAMES,
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

    # ========== 步骤4: 生成 data.yaml 已经在 split_dataset 中完成了 ==========
    print(f"\n[步骤4] data.yaml 已生成: {os.path.join(OUTPUT_DIR, 'data.yaml')}")

    # ========== 步骤5: 清理临时目录 ==========
    print("\n[步骤5] 清理临时目录...")
    if os.path.exists(temp_label_dir):
        shutil.rmtree(temp_label_dir)
        print(f"临时目录已清理: {temp_label_dir}")

    # ========== 完成 ==========
    print("\n" + "=" * 60)
    print("转换流程完成！")
    print(f"最终数据集位置: {OUTPUT_DIR}")
    print("目录结构:")
    print(f"  {OUTPUT_DIR}/")
    print(f"  ├── images/")
    print(f"  │   ├── train/")
    print(f"  │   ├── val/")
    print(f"  │   └── test/")
    print(f"  ├── labels/")
    print(f"  │   ├── train/")
    print(f"  │   ├── val/")
    print(f"  │   └── test/")
    print(f"  └── data.yaml")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    exit(main())
