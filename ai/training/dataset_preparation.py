"""
dataset_preparation.py — Dataset Collection, Validation & Splitting for DeepGuard AI.

Downloads and organizes face image datasets from multiple public sources:
  1. FaceForensics++ (existing local frames)
  2. HuggingFace Datasets (140k Real and Fake Faces, OpenForensics, etc.)
  3. Local directory ingestion (user-provided images)

Performs:
  - Format validation (JPEG/PNG decoding, min size, corruption checks)
  - SHA256 deduplication across all sources
  - Class balance verification
  - Train/Val/Test split (70/15/15) with identity-aware splitting
  - Manifest CSV generation with metadata

Usage:
    python dataset_preparation.py --config configs/train_config.yaml
    python dataset_preparation.py --source huggingface --max-per-class 1000
    python dataset_preparation.py --source local --real-dir /path/to/real --fake-dir /path/to/fake
"""

import os
import sys
import csv
import json
import shutil
import hashlib
import logging
import argparse
import random
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Project root detection
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DATASETS_DIR = PROJECT_ROOT / "ai" / "datasets"
EVAL_DIR = PROJECT_ROOT / "ai" / "evaluation"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MIN_IMAGE_SIZE = (64, 64)  # Minimum width x height


@dataclass
class ImageRecord:
    """Metadata for a single validated image."""
    path: Path
    label: int          # 0=real, 1=fake
    source: str         # "ff++", "huggingface", "local", etc.
    sha256: str
    width: int
    height: int
    file_size: int
    identity: Optional[str] = None  # For identity-aware splitting


@dataclass
class DatasetStats:
    """Statistics for the prepared dataset."""
    total_scanned: int = 0
    total_valid: int = 0
    total_corrupt: int = 0
    total_too_small: int = 0
    total_duplicates: int = 0
    real_count: int = 0
    fake_count: int = 0
    train_real: int = 0
    train_fake: int = 0
    val_real: int = 0
    val_fake: int = 0
    test_real: int = 0
    test_fake: int = 0
    sources: Dict[str, int] = field(default_factory=dict)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file for deduplication."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_image(file_path: Path) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Validate that a file is a decodable image meeting minimum quality criteria.
    Returns (is_valid, (width, height)) or (False, None).
    """
    try:
        if file_path.stat().st_size == 0:
            return False, None
        if file_path.stat().st_size < 1024:  # Files under 1KB are suspicious
            return False, None

        img = Image.open(file_path)
        img.verify()  # Check structural integrity

        # Re-open after verify (verify closes internal state)
        img = Image.open(file_path)
        img.load()  # Force full pixel decoding

        w, h = img.size
        if w < MIN_IMAGE_SIZE[0] or h < MIN_IMAGE_SIZE[1]:
            return False, None

        return True, (w, h)
    except Exception:
        return False, None


def scan_directory(
    directory: Path,
    label: int,
    source: str,
    seen_hashes: Set[str],
    stats: DatasetStats,
    max_count: Optional[int] = None,
) -> List[ImageRecord]:
    """
    Scan a directory for valid images, deduplicating by SHA256.
    """
    records = []
    if not directory.is_dir():
        logger.warning("Directory not found: %s", directory)
        return records

    image_files = sorted([
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ])

    if max_count:
        random.shuffle(image_files)
        image_files = image_files[:max_count * 2]  # Scan extra for filtering

    for img_path in image_files:
        if max_count and len(records) >= max_count:
            break

        stats.total_scanned += 1

        # Validate image
        is_valid, dimensions = validate_image(img_path)
        if not is_valid:
            if dimensions is None:
                stats.total_corrupt += 1
            else:
                stats.total_too_small += 1
            continue

        # Deduplication
        file_hash = compute_sha256(img_path)
        if file_hash in seen_hashes:
            stats.total_duplicates += 1
            continue
        seen_hashes.add(file_hash)

        w, h = dimensions
        # Extract identity from filename if possible (FF++ format: XXXX_YYYY_frame.jpg)
        identity = None
        name_parts = img_path.stem.split("_")
        if len(name_parts) >= 2:
            identity = name_parts[0]

        records.append(ImageRecord(
            path=img_path,
            label=label,
            source=source,
            sha256=file_hash,
            width=w,
            height=h,
            file_size=img_path.stat().st_size,
            identity=identity,
        ))

    logger.info(
        "Scanned %s: %d valid images (%s, label=%d)",
        directory.name, len(records), source, label,
    )
    return records


def collect_existing_evaluation_images(seen_hashes: Set[str], stats: DatasetStats) -> List[ImageRecord]:
    """Collect the existing FF++ evaluation images as seed data."""
    records = []
    real_dir = EVAL_DIR / "real"
    manip_dir = EVAL_DIR / "manipulated"

    records.extend(scan_directory(real_dir, label=0, source="ff++_eval", seen_hashes=seen_hashes, stats=stats))
    records.extend(scan_directory(manip_dir, label=1, source="ff++_eval", seen_hashes=seen_hashes, stats=stats))

    return records


def download_huggingface_dataset(
    max_per_class: int,
    seen_hashes: Set[str],
    stats: DatasetStats,
) -> List[ImageRecord]:
    """
    Download face images from HuggingFace datasets.
    Uses '140k Real and Fake Faces' dataset (MIT license).
    """
    records = []
    hf_staging = DATASETS_DIR / "_hf_staging"
    hf_staging.mkdir(parents=True, exist_ok=True)

    try:
        from datasets import load_dataset
        logger.info("Downloading HuggingFace dataset: 140k-real-and-fake-faces...")

        # Load dataset
        ds = load_dataset("Xicor9/140k-real-and-fake-faces", split="train", streaming=True)

        real_count = 0
        fake_count = 0
        idx = 0

        for sample in ds:
            if real_count >= max_per_class and fake_count >= max_per_class:
                break

            label = sample.get("label", None)
            image = sample.get("image", None)

            if label is None or image is None:
                continue

            # label: 0=real, 1=fake
            if label == 0 and real_count >= max_per_class:
                continue
            if label == 1 and fake_count >= max_per_class:
                continue

            # Save image
            class_name = "real" if label == 0 else "fake"
            save_path = hf_staging / class_name / f"hf_{idx:06d}.jpg"
            save_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(image, Image.Image):
                img = image.convert("RGB")
            else:
                continue

            img.save(save_path, "JPEG", quality=95)
            stats.total_scanned += 1

            # Validate and deduplicate
            is_valid, dims = validate_image(save_path)
            if not is_valid:
                save_path.unlink(missing_ok=True)
                stats.total_corrupt += 1
                idx += 1
                continue

            file_hash = compute_sha256(save_path)
            if file_hash in seen_hashes:
                save_path.unlink(missing_ok=True)
                stats.total_duplicates += 1
                idx += 1
                continue
            seen_hashes.add(file_hash)

            w, h = dims
            records.append(ImageRecord(
                path=save_path,
                label=label,
                source="huggingface_140k",
                sha256=file_hash,
                width=w, height=h,
                file_size=save_path.stat().st_size,
            ))

            if label == 0:
                real_count += 1
            else:
                fake_count += 1
            idx += 1

            if idx % 100 == 0:
                logger.info("HuggingFace download progress: %d real, %d fake", real_count, fake_count)

        logger.info("HuggingFace total: %d real, %d fake", real_count, fake_count)

    except ImportError:
        logger.warning(
            "HuggingFace 'datasets' library not installed. "
            "Install with: pip install datasets"
        )
    except Exception as exc:
        logger.error("HuggingFace download failed: %s", exc)

    return records


def identity_aware_split(
    records: List[ImageRecord],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    # test_ratio = 1.0 - train_ratio - val_ratio
) -> Tuple[List[ImageRecord], List[ImageRecord], List[ImageRecord]]:
    """
    Split records into train/val/test sets.
    When identity information is available, ensures no identity leaks across splits.
    Falls back to random split when identities are unavailable.
    """
    # Group by identity
    identity_groups: Dict[str, List[ImageRecord]] = defaultdict(list)
    no_identity: List[ImageRecord] = []

    for rec in records:
        if rec.identity:
            identity_groups[rec.identity].append(rec)
        else:
            no_identity.append(rec)

    # Shuffle identities
    identities = list(identity_groups.keys())
    random.shuffle(identities)

    # Split identities
    n_ids = len(identities)
    n_train = int(n_ids * train_ratio)
    n_val = int(n_ids * val_ratio)

    train_ids = set(identities[:n_train])
    val_ids = set(identities[n_train:n_train + n_val])
    test_ids = set(identities[n_train + n_val:])

    train, val, test = [], [], []
    for id_str, recs in identity_groups.items():
        if id_str in train_ids:
            train.extend(recs)
        elif id_str in val_ids:
            val.extend(recs)
        else:
            test.extend(recs)

    # Split non-identity records randomly
    random.shuffle(no_identity)
    n_ni = len(no_identity)
    n_ni_train = int(n_ni * train_ratio)
    n_ni_val = int(n_ni * val_ratio)

    train.extend(no_identity[:n_ni_train])
    val.extend(no_identity[n_ni_train:n_ni_train + n_ni_val])
    test.extend(no_identity[n_ni_train + n_ni_val:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


def copy_to_split_dirs(
    train: List[ImageRecord],
    val: List[ImageRecord],
    test: List[ImageRecord],
    base_dir: Path,
) -> None:
    """Copy images into the train/val/test directory structure."""
    for split_name, split_records in [("train", train), ("val", val), ("test", test)]:
        for rec in split_records:
            class_name = "real" if rec.label == 0 else "fake"
            dest_dir = base_dir / split_name / class_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Use source-prefixed filename to avoid collisions
            dest_name = f"{rec.source}_{rec.path.stem}{rec.path.suffix}"
            dest_path = dest_dir / dest_name

            if not dest_path.exists():
                shutil.copy2(str(rec.path), str(dest_path))


def write_manifest(records: List[ImageRecord], output_path: Path, split_name: str) -> None:
    """Write a CSV manifest of all images in a split."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "filename", "label", "label_name", "source", "sha256",
            "width", "height", "file_size", "identity", "split",
        ])
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "filename": rec.path.name,
                "label": rec.label,
                "label_name": "real" if rec.label == 0 else "fake",
                "source": rec.source,
                "sha256": rec.sha256,
                "width": rec.width,
                "height": rec.height,
                "file_size": rec.file_size,
                "identity": rec.identity or "",
                "split": split_name,
            })


def main():
    parser = argparse.ArgumentParser(description="DeepGuard AI Dataset Preparation")
    parser.add_argument("--source", choices=["local", "huggingface", "all"], default="all",
                        help="Data source to collect from")
    parser.add_argument("--max-per-class", type=int, default=1000,
                        help="Maximum images per class to download (for HF)")
    parser.add_argument("--real-dir", type=str, default=None,
                        help="Local directory with real images")
    parser.add_argument("--fake-dir", type=str, default=None,
                        help="Local directory with fake images")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-hf", action="store_true",
                        help="Skip HuggingFace download")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    stats = DatasetStats()
    seen_hashes: Set[str] = set()
    all_records: List[ImageRecord] = []

    logger.info("=" * 70)
    logger.info("DeepGuard AI — Dataset Preparation Pipeline")
    logger.info("=" * 70)

    # Step 1: Collect existing FF++ evaluation images
    logger.info("\n[1/3] Collecting existing FaceForensics++ evaluation images...")
    existing = collect_existing_evaluation_images(seen_hashes, stats)
    all_records.extend(existing)
    stats.sources["ff++_eval"] = len(existing)

    # Step 2: Download from HuggingFace (if requested)
    if args.source in ("huggingface", "all") and not args.skip_hf:
        logger.info("\n[2/3] Downloading from HuggingFace datasets...")
        hf_records = download_huggingface_dataset(args.max_per_class, seen_hashes, stats)
        all_records.extend(hf_records)
        stats.sources["huggingface_140k"] = len(hf_records)

    # Step 3: Ingest local directories (if provided)
    if args.source in ("local", "all"):
        if args.real_dir:
            logger.info("\n[3/3] Ingesting local real images from %s...", args.real_dir)
            local_real = scan_directory(
                Path(args.real_dir), label=0, source="local",
                seen_hashes=seen_hashes, stats=stats, max_count=args.max_per_class,
            )
            all_records.extend(local_real)
            stats.sources["local_real"] = len(local_real)

        if args.fake_dir:
            logger.info("Ingesting local fake images from %s...", args.fake_dir)
            local_fake = scan_directory(
                Path(args.fake_dir), label=1, source="local",
                seen_hashes=seen_hashes, stats=stats, max_count=args.max_per_class,
            )
            all_records.extend(local_fake)
            stats.sources["local_fake"] = len(local_fake)

    # Tally
    stats.total_valid = len(all_records)
    stats.real_count = sum(1 for r in all_records if r.label == 0)
    stats.fake_count = sum(1 for r in all_records if r.label == 1)

    logger.info("\n" + "=" * 70)
    logger.info("COLLECTION SUMMARY")
    logger.info("  Total scanned:    %d", stats.total_scanned)
    logger.info("  Total valid:      %d", stats.total_valid)
    logger.info("  Total corrupt:    %d", stats.total_corrupt)
    logger.info("  Total too small:  %d", stats.total_too_small)
    logger.info("  Total duplicates: %d", stats.total_duplicates)
    logger.info("  Real images:      %d", stats.real_count)
    logger.info("  Fake images:      %d", stats.fake_count)
    logger.info("  Sources: %s", dict(stats.sources))
    logger.info("=" * 70)

    if stats.total_valid < 20:
        logger.error("Too few valid images (%d). Aborting split.", stats.total_valid)
        sys.exit(1)

    # Step 4: Identity-aware train/val/test split
    logger.info("\nSplitting into train/val/test (%.0f/%.0f/%.0f)...",
                args.train_ratio * 100, args.val_ratio * 100,
                (1 - args.train_ratio - args.val_ratio) * 100)

    train, val, test = identity_aware_split(all_records, args.train_ratio, args.val_ratio)

    stats.train_real = sum(1 for r in train if r.label == 0)
    stats.train_fake = sum(1 for r in train if r.label == 1)
    stats.val_real = sum(1 for r in val if r.label == 0)
    stats.val_fake = sum(1 for r in val if r.label == 1)
    stats.test_real = sum(1 for r in test if r.label == 0)
    stats.test_fake = sum(1 for r in test if r.label == 1)

    logger.info("  Train: %d (real=%d, fake=%d)", len(train), stats.train_real, stats.train_fake)
    logger.info("  Val:   %d (real=%d, fake=%d)", len(val), stats.val_real, stats.val_fake)
    logger.info("  Test:  %d (real=%d, fake=%d)", len(test), stats.test_real, stats.test_fake)

    # Step 5: Copy files to split directories
    logger.info("\nCopying to split directories...")
    copy_to_split_dirs(train, val, test, DATASETS_DIR)

    # Step 6: Write manifests
    manifest_dir = DATASETS_DIR / "manifests"
    write_manifest(train, manifest_dir / "train_manifest.csv", "train")
    write_manifest(val, manifest_dir / "val_manifest.csv", "val")
    write_manifest(test, manifest_dir / "test_manifest.csv", "test")

    # Step 7: Save stats
    stats_dict = {
        "total_scanned": stats.total_scanned,
        "total_valid": stats.total_valid,
        "total_corrupt": stats.total_corrupt,
        "total_too_small": stats.total_too_small,
        "total_duplicates": stats.total_duplicates,
        "class_distribution": {"real": stats.real_count, "fake": stats.fake_count},
        "splits": {
            "train": {"real": stats.train_real, "fake": stats.train_fake, "total": len(train)},
            "val": {"real": stats.val_real, "fake": stats.val_fake, "total": len(val)},
            "test": {"real": stats.test_real, "fake": stats.test_fake, "total": len(test)},
        },
        "sources": dict(stats.sources),
    }
    stats_path = manifest_dir / "dataset_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w") as f:
        json.dump(stats_dict, f, indent=2)

    logger.info("\n✅ Dataset preparation complete!")
    logger.info("   Stats: %s", stats_path)
    logger.info("   Data:  %s", DATASETS_DIR)


if __name__ == "__main__":
    main()
