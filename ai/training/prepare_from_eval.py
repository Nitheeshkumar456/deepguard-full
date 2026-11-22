"""
prepare_from_eval.py — Lightweight dataset bootstrapper for DeepGuard AI.

Since we cannot download large external datasets (FaceForensics++, Celeb-DF, DFDC)
without credentials/licenses, this script:
  1. Augments the existing 50 real + 50 fake evaluation frames into a usable train/val/test split.
  2. Applies 8 deterministic augmentation variants per image to expand to ~400 real + ~400 fake.
  3. Writes proper directory structure for train.py (datasets/train/real, datasets/train/fake, etc.)
  4. Generates a dataset manifest CSV.

This gives us ~560 train + ~120 val + ~120 test images — sufficient for fine-tuning.

Usage:
    python prepare_from_eval.py
    python prepare_from_eval.py --max-augmentations 12 --seed 42
"""

import os
import sys
import csv
import json
import hashlib
import logging
import argparse
import random
import shutil
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
EVAL_DIR = PROJECT_ROOT / "ai" / "evaluation"
DATASETS_DIR = PROJECT_ROOT / "ai" / "datasets"

# Source directories
REAL_DIR = EVAL_DIR / "real"
MANIPULATED_DIR = EVAL_DIR / "manipulated"
ORIGINAL_C23_DIR = EVAL_DIR / "original_c23_subset"
MANIPULATED_C23_DIR = EVAL_DIR / "manipulated_c23_subset"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def sha256_of_array(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


def augment_image(img: Image.Image, variant: int, seed: int) -> Image.Image:
    """
    Apply one of several deterministic augmentation variants to a PIL image.
    Using seed for reproducibility.
    """
    rng = random.Random(seed * 100 + variant)
    img = img.convert("RGB")

    if variant == 0:
        # Horizontal flip
        img = ImageOps.mirror(img)

    elif variant == 1:
        # Rotation ±10°
        angle = rng.uniform(-10, 10)
        img = img.rotate(angle, expand=False, fillcolor=(0, 0, 0))

    elif variant == 2:
        # Brightness jitter
        factor = rng.uniform(0.75, 1.25)
        img = ImageEnhance.Brightness(img).enhance(factor)

    elif variant == 3:
        # Contrast jitter
        factor = rng.uniform(0.75, 1.25)
        img = ImageEnhance.Contrast(img).enhance(factor)

    elif variant == 4:
        # Gaussian blur (slight)
        radius = rng.uniform(0.5, 1.2)
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))

    elif variant == 5:
        # Horizontal flip + brightness
        img = ImageOps.mirror(img)
        factor = rng.uniform(0.85, 1.15)
        img = ImageEnhance.Brightness(img).enhance(factor)

    elif variant == 6:
        # Center crop + resize back to original size
        w, h = img.size
        crop_margin_x = int(w * rng.uniform(0.05, 0.12))
        crop_margin_y = int(h * rng.uniform(0.05, 0.12))
        img = img.crop((crop_margin_x, crop_margin_y,
                        w - crop_margin_x, h - crop_margin_y))
        img = img.resize((w, h), Image.BICUBIC)

    elif variant == 7:
        # JPEG compression artifact simulation
        import io
        quality = rng.randint(65, 90)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")

    elif variant == 8:
        # Saturation jitter
        factor = rng.uniform(0.7, 1.3)
        img = ImageEnhance.Color(img).enhance(factor)

    elif variant == 9:
        # Sharpness jitter
        factor = rng.uniform(0.6, 1.4)
        img = ImageEnhance.Sharpness(img).enhance(factor)

    elif variant == 10:
        # Hue shift via L*a*b* approximation
        arr = np.array(img).astype(np.float32)
        shift = rng.randint(-15, 15)
        arr[:, :, 0] = np.clip(arr[:, :, 0] + shift, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8))

    elif variant == 11:
        # Mirror + contrast
        img = ImageOps.mirror(img)
        factor = rng.uniform(0.85, 1.15)
        img = ImageEnhance.Contrast(img).enhance(factor)

    return img


def scan_source_dir(directory: Path, label: int, source: str, seen_hashes: set) -> List[Tuple[Path, int, str]]:
    """Scan a directory for valid images, skip duplicates."""
    records = []
    if not directory.is_dir():
        logger.warning("Source directory not found: %s", directory)
        return records

    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            try:
                img = Image.open(f).convert("RGB")
                img.load()
                h = sha256_of_array(np.array(img))
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    records.append((f, label, source))
            except Exception as e:
                logger.debug("Skipping corrupt image %s: %s", f.name, e)

    logger.info("Scanned %s: %d valid images (label=%d, source=%s)", directory.name, len(records), label, source)
    return records


def main():
    parser = argparse.ArgumentParser(description="DeepGuard AI — Dataset Bootstrap from Evaluation Images")
    parser.add_argument("--max-augmentations", type=int, default=8,
                        help="Number of augmentation variants per original image (max 12)")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clean", action="store_true",
                        help="Clean existing dataset dirs before writing")
    args = parser.parse_args()

    args.max_augmentations = min(args.max_augmentations, 12)
    random.seed(args.seed)
    np.random.seed(args.seed)

    logger.info("=" * 70)
    logger.info("DeepGuard AI — Dataset Bootstrapper")
    logger.info("  Source: Augmenting existing evaluation images")
    logger.info("  Augmentation variants per image: %d", args.max_augmentations)
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Collect original images
    # ------------------------------------------------------------------
    seen_hashes: set = set()
    originals: List[Tuple[Path, int, str]] = []

    originals.extend(scan_source_dir(REAL_DIR, label=0, source="ff++_eval_real", seen_hashes=seen_hashes))
    originals.extend(scan_source_dir(MANIPULATED_DIR, label=1, source="ff++_eval_manip", seen_hashes=seen_hashes))

    # Also pick up any extra c23 subset images
    originals.extend(scan_source_dir(ORIGINAL_C23_DIR, label=0, source="ff++_c23_real", seen_hashes=seen_hashes))
    originals.extend(scan_source_dir(MANIPULATED_C23_DIR, label=1, source="ff++_c23_manip", seen_hashes=seen_hashes))

    real_originals = [r for r in originals if r[1] == 0]
    fake_originals = [r for r in originals if r[1] == 1]

    logger.info("\nOriginals collected: %d real, %d fake", len(real_originals), len(fake_originals))

    if len(originals) < 20:
        logger.error("Not enough source images found (need at least 20). Check evaluation directories.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Generate augmented records
    # ------------------------------------------------------------------
    all_records: List[Tuple[Path, np.ndarray, int, str]] = []

    for file_path, label, source in originals:
        try:
            original_img = Image.open(file_path).convert("RGB")
            # Include original
            all_records.append((file_path, np.array(original_img), label, source + "_orig"))
            # Add augmentations
            for v in range(args.max_augmentations):
                aug_img = augment_image(original_img.copy(), v, seed=args.seed + label * 1000)
                all_records.append((file_path, np.array(aug_img), label, source + f"_aug{v}"))
        except Exception as e:
            logger.warning("Failed to process %s: %s", file_path.name, e)

    # Shuffle
    random.shuffle(all_records)

    real_all = [r for r in all_records if r[2] == 0]
    fake_all = [r for r in all_records if r[2] == 1]
    logger.info("\nAfter augmentation: %d real, %d fake total", len(real_all), len(fake_all))

    # Balance classes
    min_count = min(len(real_all), len(fake_all))
    real_all = real_all[:min_count]
    fake_all = fake_all[:min_count]
    balanced = real_all + fake_all
    random.shuffle(balanced)
    logger.info("After balancing: %d total (%d per class)", len(balanced), min_count)

    # ------------------------------------------------------------------
    # Step 3: Train/Val/Test split
    # ------------------------------------------------------------------
    n = len(balanced)
    n_train = int(n * args.train_ratio)
    n_val = int(n * args.val_ratio)
    n_test = n - n_train - n_val

    train_records = balanced[:n_train]
    val_records = balanced[n_train:n_train + n_val]
    test_records = balanced[n_train + n_val:]

    logger.info("\nSplit: train=%d, val=%d, test=%d", len(train_records), len(val_records), len(test_records))

    # ------------------------------------------------------------------
    # Step 4: Write to disk
    # ------------------------------------------------------------------
    if args.clean:
        for split in ["train", "val", "test"]:
            split_dir = DATASETS_DIR / split
            if split_dir.exists():
                shutil.rmtree(str(split_dir))
                logger.info("Cleaned: %s", split_dir)

    # Create directories
    for split in ["train", "val", "test"]:
        for cls in ["real", "fake"]:
            (DATASETS_DIR / split / cls).mkdir(parents=True, exist_ok=True)

    manifest_rows = []

    def write_split(records, split_name):
        counters = {"real": 0, "fake": 0}
        for (src_path, arr, label, source) in records:
            cls = "real" if label == 0 else "fake"
            idx = counters[cls]
            counters[cls] += 1
            fname = f"{source}_{src_path.stem}_{idx:04d}.jpg"
            dest = DATASETS_DIR / split_name / cls / fname
            try:
                img = Image.fromarray(arr.astype(np.uint8)).convert("RGB")
                img.save(str(dest), "JPEG", quality=95)
                manifest_rows.append({
                    "split": split_name,
                    "filename": fname,
                    "label": label,
                    "label_name": cls,
                    "source": source,
                    "original": src_path.name,
                })
            except Exception as e:
                logger.warning("Failed to write %s: %s", dest, e)

    write_split(train_records, "train")
    write_split(val_records, "val")
    write_split(test_records, "test")

    # ------------------------------------------------------------------
    # Step 5: Write manifests
    # ------------------------------------------------------------------
    manifest_dir = DATASETS_DIR / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = manifest_dir / "augmented_manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["split", "filename", "label", "label_name", "source", "original"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    # Dataset stats
    stats = {
        "source_images": {"real": len(real_originals), "fake": len(fake_originals)},
        "augmentation_variants": args.max_augmentations,
        "total_after_augmentation": {"real": len(real_all), "fake": len(fake_all)},
        "after_balancing": min_count * 2,
        "splits": {
            "train": {
                "total": len(train_records),
                "real": sum(1 for r in train_records if r[2] == 0),
                "fake": sum(1 for r in train_records if r[2] == 1),
            },
            "val": {
                "total": len(val_records),
                "real": sum(1 for r in val_records if r[2] == 0),
                "fake": sum(1 for r in val_records if r[2] == 1),
            },
            "test": {
                "total": len(test_records),
                "real": sum(1 for r in test_records if r[2] == 0),
                "fake": sum(1 for r in test_records if r[2] == 1),
            },
        },
        "seed": args.seed,
    }
    stats_path = manifest_dir / "dataset_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    logger.info("\n✅ Dataset bootstrap complete!")
    logger.info("   Train: %d images (real=%d, fake=%d)",
                stats["splits"]["train"]["total"],
                stats["splits"]["train"]["real"],
                stats["splits"]["train"]["fake"])
    logger.info("   Val:   %d images (real=%d, fake=%d)",
                stats["splits"]["val"]["total"],
                stats["splits"]["val"]["real"],
                stats["splits"]["val"]["fake"])
    logger.info("   Test:  %d images (real=%d, fake=%d)",
                stats["splits"]["test"]["total"],
                stats["splits"]["test"]["real"],
                stats["splits"]["test"]["fake"])
    logger.info("   Manifest: %s", manifest_path)
    logger.info("   Stats:    %s", stats_path)
    logger.info("\n➜  Now run:  python train.py  (from project root or ai/training/)")


if __name__ == "__main__":
    main()
