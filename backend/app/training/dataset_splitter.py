"""
数据集划分工具模块

提供 DatasetSplitter 类，用于将目标检测数据集按自定义比例
划分为训练集、验证集和测试集，并生成 YOLO 格式的 data.yaml 配置文件。
"""
import random
import shutil
from pathlib import Path

import yaml

from app.core.logger import get_logger

logger = get_logger(__name__)

# 支持的图像文件扩展名
_SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


class DatasetSplitter:
    """数据集划分器

    将图像与标注文件按指定比例随机划分为 train/val/test 三个子集，
    并在输出目录中生成 data.yaml 配置文件。
    """

    @staticmethod
    def split_dataset(
        image_dir: str,
        label_dir: str,
        output_dir: str,
        class_names: list,
        ratios: tuple = (0.8, 0.1, 0.1),
        seed: int = 42,
    ) -> dict:
        """
        将数据集按比例划分为训练集、验证集和测试集

        参数：
            image_dir: 原始图像目录路径
            label_dir: 原始标注目录路径（.txt 格式）
            output_dir: 输出根目录，将在其下创建 images/、labels/ 子目录及 data.yaml
            class_names: 类别名称列表，顺序即为类别索引
            ratios: 三元组 (train, val, test)，三者和应为 1.0
            seed: 随机种子，保证划分可复现

        返回：
            dict: {"train": N, "val": N, "test": N, "total": N} 统计信息

        异常：
            ValueError: 图像目录不存在、无有效图像、或 ratios 之和不为 1.0
        """
        image_dir_path = Path(image_dir)
        label_dir_path = Path(label_dir)
        output_dir_path = Path(output_dir)

        # ── 校验输入 ──────────────────────────────────
        if not image_dir_path.is_dir():
            raise ValueError(f"图像目录不存在: {image_dir}")

        if abs(sum(ratios) - 1.0) > 1e-9:
            raise ValueError(f"ratios 之和必须为 1.0，当前为 {sum(ratios)}")

        # ── 收集有效图像文件 ───────────────────────────
        image_files = sorted(
            p
            for p in image_dir_path.iterdir()
            if p.is_file() and p.suffix.lower() in _SUPPORTED_IMAGE_EXTS
        )

        if not image_files:
            raise ValueError(f"图像目录中未找到支持的图像文件: {image_dir}")

        logger.info(
            "找到 %d 张图像，准备按 train:val:test = %.2f:%.2f:%.2f 划分",
            len(image_files),
            ratios[0],
            ratios[1],
            ratios[2],
        )

        # ── 随机打乱 ──────────────────────────────────
        random.seed(seed)
        shuffled = image_files[:]  # 浅拷贝，避免修改原列表
        random.shuffle(shuffled)

        # ── 按比例划分 ────────────────────────────────
        total = len(shuffled)
        train_end = round(total * ratios[0])
        val_end = train_end + round(total * ratios[1])

        splits = {
            "train": shuffled[:train_end],
            "val": shuffled[train_end:val_end],
            "test": shuffled[val_end:],
        }

        # ── 创建输出目录结构 ──────────────────────────
        for subset in ("train", "val", "test"):
            (output_dir_path / "images" / subset).mkdir(parents=True, exist_ok=True)
            (output_dir_path / "labels" / subset).mkdir(parents=True, exist_ok=True)

        # ── 复制图像与标注文件 ────────────────────────
        for subset_name, files in splits.items():
            for img_path in files:
                # 复制图像
                dst_img = (
                    output_dir_path / "images" / subset_name / img_path.name
                )
                shutil.copy2(img_path, dst_img)

                # 复制/创建标注文件
                label_name = img_path.stem + ".txt"
                src_label = label_dir_path / label_name
                dst_label = (
                    output_dir_path / "labels" / subset_name / label_name
                )

                if src_label.is_file():
                    shutil.copy2(src_label, dst_label)
                else:
                    # 无标注则创建空文件
                    dst_label.touch()

            logger.info(
                "%s 集: %d 张图像已复制",
                subset_name,
                len(files),
            )

        # ── 生成 data.yaml ────────────────────────────
        data_yaml = {
            "path": str(output_dir_path.resolve()),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "nc": len(class_names),
            "names": {i: name for i, name in enumerate(class_names)},
        }

        yaml_path = output_dir_path / "data.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data_yaml,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        logger.info("data.yaml 已生成: %s", yaml_path)

        # ── 返回统计信息 ──────────────────────────────
        stats = {
            "train": len(splits["train"]),
            "val": len(splits["val"]),
            "test": len(splits["test"]),
            "total": total,
        }
        logger.info("数据集划分完成: %s", stats)
        return stats