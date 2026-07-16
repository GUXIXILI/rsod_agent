"""
火灾烟雾检测模型运行时参数校验

提供图像尺寸、批处理大小、推理设备的统一校验函数。
所有校验函数在参数无效时抛出 ValueError，由调用方统一处理。
"""

import re

# 图像尺寸范围：YOLO 要求尺寸为 32 的倍数
MIN_IMAGE_SIZE = 320
MAX_IMAGE_SIZE = 1280
# 评估批处理大小上限
MAX_BATCH_SIZE = 64
# 设备参数格式：cpu 或纯数字（CUDA 设备编号）
DEVICE_PATTERN = re.compile(r"^(cpu|\d+)$")


def validate_image_size(imgsz: int) -> None:
    """
    校验模型推理图像尺寸。

    约束条件：
    - 必须为整数
    - 范围在 [320, 1280] 之间
    - 必须是 32 的倍数（YOLO 模型架构要求）

    Args:
        imgsz: 图像尺寸

    Raises:
        ValueError: 尺寸不符合约束
    """
    if (
        not isinstance(imgsz, int)
        or isinstance(imgsz, bool)
        or imgsz < MIN_IMAGE_SIZE
        or imgsz > MAX_IMAGE_SIZE
        or imgsz % 32 != 0
    ):
        raise ValueError(
            "imgsz must be between 320 and 1280 and divisible by 32"
        )


def validate_batch_size(batch: int) -> None:
    """
    校验模型评估批处理大小。

    约束条件：
    - 必须为整数
    - 范围在 [1, 64] 之间

    Args:
        batch: 批处理大小

    Raises:
        ValueError: 批处理大小不符合约束
    """
    if (
        not isinstance(batch, int)
        or isinstance(batch, bool)
        or batch < 1
        or batch > MAX_BATCH_SIZE
    ):
        raise ValueError("batch must be between 1 and 64")


def validate_device(device: str) -> None:
    """
    校验推理设备参数。

    合法值：
    - "cpu"：纯 CPU 推理
    - "0", "1", ...：CUDA 设备编号

    Args:
        device: 推理设备标识符

    Raises:
        ValueError: 设备参数格式不合法
    """
    if not isinstance(device, str) or DEVICE_PATTERN.fullmatch(device) is None:
        raise ValueError("device must be 'cpu' or a non-negative CUDA index")
