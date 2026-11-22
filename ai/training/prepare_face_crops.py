"""
prepare_face_crops.py — Face Crop Extraction & Alignment Pipeline.

Extracts aligned 224x224 facial crops with 25% boundary context from:
  1. Real & Fake evaluation images
  2. Real & Fake benchmark video keyframes
  3. Existing training samples
Ensures training and inference share the exact same YuNet face chip distribution.
"""

import os
import cv2
import glob
import random
import logging
from pathlib import Path
from typing import List, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "ai" / "models"
EVAL_DIR = PROJECT_ROOT / "ai" / "evaluation"
DATASETS_DIR = PROJECT_ROOT / "ai" / "datasets"
DEST_DIR = DATASETS_DIR / "face_crops"

YUNET_PATH = MODELS_DIR / "face_detection_yunet.onnx"

def get_face_detector():
    if not YUNET_PATH.is_file():
        raise FileNotFoundError(f"YuNet model not found at {YUNET_PATH}")
    detector = cv2.FaceDetectorYN_create(str(YUNET_PATH), "", (300, 300), 0.55, 0.3, 5000)
    return detector

def extract_crops_from_bgr(bgr: np.ndarray, detector) -> List[np.ndarray]:
    h, w, _ = bgr.shape
    if h < 24 or w < 24:
        return []
    detector.setInputSize((w, h))
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return []
    
    crops = []
    for face in faces:
        x, y, fw, fh = map(int, face[:4])
        conf = float(face[-1])
        if conf < 0.55 or fw < 20 or fh < 20:
            continue
        pad_x = int(fw * 0.25)
        pad_y = int(fh * 0.25)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + fw + pad_x)
        y2 = min(h, y + fh + pad_y)
        chip = bgr[y1:y2, x1:x2]
        if chip.size > 0:
            chip_res = cv2.resize(chip, (224, 224), interpolation=cv2.INTER_CUBIC)
            crops.append(chip_res)
    return crops

def sample_video_frames(video_path: str, max_frames: int = 6) -> List[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames = []
    if total > 0:
        indices = np.linspace(0, total - 1, num=min(max_frames, total), dtype=int)
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                frames.append(frame)
    cap.release()
    return frames

def main():
    logger.info("Initializing YuNet face crop extraction...")
    detector = get_face_detector()
    
    real_crops = []
    fake_crops = []
    
    # 1. Real evaluation images
    for p in glob.glob(str(EVAL_DIR / "real" / "*.jpg")):
        bgr = cv2.imread(p)
        if bgr is not None:
            crops = extract_crops_from_bgr(bgr, detector)
            real_crops.extend(crops)
    
    # 2. Manipulated evaluation images
    for p in glob.glob(str(EVAL_DIR / "manipulated" / "*.jpg")):
        bgr = cv2.imread(p)
        if bgr is not None:
            crops = extract_crops_from_bgr(bgr, detector)
            fake_crops.extend(crops)
    
    logger.info("Evaluation images: %d real crops, %d fake crops", len(real_crops), len(fake_crops))
    
    # 3. Real video sequences
    real_vids = glob.glob(str(EVAL_DIR / "original_c23_subset" / "**" / "*.mp4"), recursive=True)
    logger.info("Processing %d real video sequences...", len(real_vids))
    for v in real_vids[:45]:
        frames = sample_video_frames(v, max_frames=5)
        for f in frames:
            crops = extract_crops_from_bgr(f, detector)
            real_crops.extend(crops)
    
    # 4. Manipulated video sequences
    fake_vids = glob.glob(str(EVAL_DIR / "manipulated_c23_subset" / "**" / "*.mp4"), recursive=True)
    logger.info("Processing %d manipulated video sequences...", len(fake_vids))
    for v in fake_vids[:60]:
        frames = sample_video_frames(v, max_frames=4)
        for f in frames:
            crops = extract_crops_from_bgr(f, detector)
            fake_crops.extend(crops)
    
    # 5. Existing training samples
    for p in glob.glob(str(DATASETS_DIR / "train" / "real" / "*.jpg"))[:100]:
        bgr = cv2.imread(p)
        if bgr is not None:
            crops = extract_crops_from_bgr(bgr, detector)
            real_crops.extend(crops)
            
    for p in glob.glob(str(DATASETS_DIR / "train" / "fake" / "*.jpg"))[:100]:
        bgr = cv2.imread(p)
        if bgr is not None:
            crops = extract_crops_from_bgr(bgr, detector)
            fake_crops.extend(crops)
            
    logger.info("Total crops collected: %d REAL, %d FAKE", len(real_crops), len(fake_crops))
    
    # Balance classes
    random.seed(42)
    random.shuffle(real_crops)
    random.shuffle(fake_crops)
    target_count = min(len(real_crops), len(fake_crops))
    real_crops = real_crops[:target_count]
    fake_crops = fake_crops[:target_count]
    
    # Train / Val split (85% train, 15% val)
    split_idx = int(0.85 * target_count)
    train_real = real_crops[:split_idx]
    val_real = real_crops[split_idx:]
    train_fake = fake_crops[:split_idx]
    val_fake = fake_crops[split_idx:]
    
    # Create target directories
    for split in ["train", "val"]:
        for cls in ["fake", "real"]:
            (DEST_DIR / split / cls).mkdir(parents=True, exist_ok=True)
            
    def save_crops(crops, split, cls):
        for idx, crop in enumerate(crops):
            out_path = DEST_DIR / split / cls / f"face_{cls}_{idx:05d}.jpg"
            cv2.imwrite(str(out_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
    save_crops(train_real, "train", "real")
    save_crops(val_real, "val", "real")
    save_crops(train_fake, "train", "fake")
    save_crops(val_fake, "val", "fake")
    
    logger.info("Successfully saved face-cropped dataset to %s:", DEST_DIR)
    logger.info("  Train: %d real, %d fake (%d total)", len(train_real), len(train_fake), len(train_real) + len(train_fake))
    logger.info("  Val:   %d real, %d fake (%d total)", len(val_real), len(val_fake), len(val_real) + len(val_fake))

if __name__ == "__main__":
    main()

