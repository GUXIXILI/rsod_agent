"""Shared validation for fire and smoke model runtime parameters."""

import re


MIN_IMAGE_SIZE = 320
MAX_IMAGE_SIZE = 1280
MAX_BATCH_SIZE = 64
DEVICE_PATTERN = re.compile(r"^(cpu|\d+)$")


def validate_image_size(imgsz: int) -> None:
    """Validate the image size accepted by model APIs and services."""
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
    """Validate the evaluation batch size."""
    if (
        not isinstance(batch, int)
        or isinstance(batch, bool)
        or batch < 1
        or batch > MAX_BATCH_SIZE
    ):
        raise ValueError("batch must be between 1 and 64")


def validate_device(device: str) -> None:
    """Accept CPU or one non-negative CUDA device index."""
    if not isinstance(device, str) or DEVICE_PATTERN.fullmatch(device) is None:
        raise ValueError("device must be 'cpu' or a non-negative CUDA index")
