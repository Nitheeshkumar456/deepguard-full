"""
image_preprocessor.py — Image loading, validation, and tensor conversion.

Handles the full preprocessing pipeline from raw file path to model-ready tensor:
  1. Load image from disk (PIL)
  2. Validate image integrity
  3. Extract metadata (dimensions, mode)
  4. Apply EXIF orientation correction
  5. Convert to RGB
  6. Resize to model input dimensions
  7. Normalize pixel values
  8. Convert to PyTorch tensor (BCHW format)

All failures raise specific exceptions from exceptions.py — no silent fallbacks.
"""

import os
import logging
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .exceptions import (
    InvalidImageError,
    CorruptFileError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Supported formats for AI analysis (PIL format names)
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF", "MPO"}

# Model input dimensions
MODEL_INPUT_SIZE: Tuple[int, int] = (224, 224)

# ImageNet normalization constants
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class ImageMetadata:
    """Metadata extracted during image preprocessing."""
    original_width: int
    original_height: int
    color_mode: str
    format: str


@dataclass
class PreprocessedImage:
    """Container for a preprocessed image ready for model inference."""
    tensor: "torch.Tensor"  # noqa: F821 — forward reference, torch imported at use-time
    metadata: ImageMetadata


def _apply_exif_orientation(image: "PIL.Image.Image") -> "PIL.Image.Image":
    """
    Apply EXIF orientation tag to the image pixels and strip the tag.
    Prevents sideways/upside-down images from producing incorrect inference.
    """
    try:
        from PIL import ImageOps
        return ImageOps.exif_transpose(image)
    except Exception:
        # If EXIF processing fails, return image as-is
        return image


def load_and_validate_image(file_path: str) -> "PIL.Image.Image":
    """
    Load an image from disk and validate it can be decoded.

    Returns the opened PIL Image object.

    Raises:
        InvalidImageError: If the file cannot be opened as an image.
        CorruptFileError: If the image data is truncated or damaged.
        UnsupportedFormatError: If the image format is not in the supported set.
    """
    from PIL import Image, UnidentifiedImageError

    # ── 1. Verify file exists ───────────────────────────────────────────────
    if not os.path.isfile(file_path):
        raise InvalidImageError(f"Image file not found at path: {file_path}")

    # ── 2. Check file is not empty ──────────────────────────────────────────
    if os.path.getsize(file_path) == 0:
        raise CorruptFileError("Image file is empty (0 bytes).")

    # ── 3. Attempt to open with PIL ─────────────────────────────────────────
    try:
        image = Image.open(file_path)
    except UnidentifiedImageError:
        raise InvalidImageError(
            "The file could not be identified as a valid image. "
            "It may be corrupted or in an unsupported format."
        )
    except (OSError, IOError) as exc:
        raise CorruptFileError(
            f"Failed to read image file: {exc}"
        )

    # ── 4. Verify the format is supported ───────────────────────────────────
    img_format = (image.format or "").upper()
    if img_format not in SUPPORTED_PIL_FORMATS:
        raise UnsupportedFormatError(
            f"Image format '{img_format or 'unknown'}' is not supported. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_PIL_FORMATS))}"
        )

    # ── 5. Force-load pixel data to detect truncation ───────────────────────
    try:
        image.load()
    except (OSError, IOError, SyntaxError) as exc:
        raise CorruptFileError(
            f"Image file appears to be truncated or damaged: {exc}"
        )

    logger.info(
        "Image loaded: %s, format=%s, size=%dx%d, mode=%s",
        file_path, img_format, image.width, image.height, image.mode,
    )
    return image


def preprocess_image(file_path: str) -> PreprocessedImage:
    """
    Full preprocessing pipeline: load → validate → orient → RGB → resize → normalize → tensor.

    Returns a PreprocessedImage containing the model-ready tensor and metadata.

    Raises:
        InvalidImageError, CorruptFileError, UnsupportedFormatError
    """
    import torch

    # ── 1. Load and validate ────────────────────────────────────────────────
    image = load_and_validate_image(file_path)

    # ── 2. Extract metadata before any transforms ───────────────────────────
    metadata = ImageMetadata(
        original_width=image.width,
        original_height=image.height,
        color_mode=image.mode,
        format=image.format or "UNKNOWN",
    )

    # ── 3. EXIF orientation correction ──────────────────────────────────────
    image = _apply_exif_orientation(image)

    # ── 4. Convert to RGB (handles RGBA, L, P, CMYK, etc.) ─────────────────
    try:
        if image.mode != "RGB":
            image = image.convert("RGB")
    except Exception as exc:
        raise InvalidImageError(
            f"Failed to convert image from {metadata.color_mode} to RGB: {exc}"
        )

    # ── 5. Resize to model input dimensions ─────────────────────────────────
    image = image.resize(MODEL_INPUT_SIZE, resample=3)  # 3 = BICUBIC

    # ── 6. Convert to numpy array and normalize ─────────────────────────────
    img_array = np.array(image, dtype=np.float32) / 255.0
    img_array = (img_array - IMAGENET_MEAN) / IMAGENET_STD

    # ── 7. Convert to PyTorch tensor: HWC → CHW → BCHW ─────────────────────
    tensor = torch.from_numpy(img_array).permute(2, 0, 1).unsqueeze(0)

    logger.info(
        "Image preprocessed: original=%dx%d → model_input=%s, dtype=%s",
        metadata.original_width, metadata.original_height,
        tuple(tensor.shape), tensor.dtype,
    )

    return PreprocessedImage(tensor=tensor, metadata=metadata)
