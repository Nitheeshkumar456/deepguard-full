"""
prepare_expanded_dataset_2k.py
Builds an identity-independent dataset of ~1,000 REAL and ~1,000 FAKE aligned face crops.
Sources:
  - FaceForensics++ Original sequences (Real, YouTube c23)
  - FaceForensics++ Face2Face manipulated sequences (Fake, c23)
  - Synthetic facial morphing & blending samples
Ensures zero identity overlap between Train, Validation, and Test splits.
"""

import os
import cv2
import json
import random
import shutil
import numpy as np
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REAL_VIDEOS_DIR = PROJECT_ROOT / "ai" / "evaluation" / "original_c23_subset" / "original_sequences" / "youtube" / "c23" / "videos"
MANIP_VIDEOS_DIR = PROJECT_ROOT / "ai" / "evaluation" / "manipulated_c23_subset" / "manipulated_sequences" / "Face2Face" / "c23" / "videos"
YUNET_PATH = PROJECT_ROOT / "ai" / "models" / "face_detection_yunet.onnx"

OUTPUT_DIR = PROJECT_ROOT / "ai" / "datasets" / "expanded_dataset_2k"

def init_yunet(w=1920, h=1080):
    detector = cv2.FaceDetectorYN_create(
        str(YUNET_PATH),
        "",
        (w, h),
        0.6,   # score threshold
        0.3,   # NMS threshold
        5000   # Top K
    )
    return detector

def extract_face_crop(bgr_image, detector, min_size=40, pad_ratio=0.25):
    h, w, _ = bgr_image.shape
    if h < min_size or w < min_size:
        return None
    detector.setInputSize((w, h))
    _, faces = detector.detect(bgr_image)
    if faces is None or len(faces) == 0:
        return None
    
    # Filter candidates by min_size
    valid = []
    for face in faces:
        x, y, fw, fh = map(int, face[:4])
        conf = float(face[-1])
        if fw >= min_size and fh >= min_size:
            valid.append((x, y, fw, fh, conf, fw * fh))
    
    if not valid:
        return None
    
    # Sort by area descending (primary subject)
    valid.sort(key=lambda item: item[5], reverse=True)
    x, y, fw, fh, conf, _ = valid[0]
    
    # Add padding
    pad_x = int(fw * pad_ratio)
    pad_y = int(fh * pad_ratio)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + fw + pad_x)
    y2 = min(h, y + fh + pad_y)
    
    chip = bgr_image[y1:y2, x1:x2]
    if chip.size == 0 or chip.shape[0] < min_size or chip.shape[1] < min_size:
        return None
    
    chip_res = cv2.resize(chip, (224, 224), interpolation=cv2.INTER_AREA)
    return chip_res

def generate_morph_sample(face_a_bgr, face_b_bgr, alpha=0.5):
    """Generates an aligned facial morph / blend sample with edge artifact."""
    res_b = cv2.resize(face_b_bgr, (224, 224))
    res_a = cv2.resize(face_a_bgr, (224, 224))
    # Alpha blend center face region
    mask = np.zeros((224, 224), dtype=np.float32)
    cv2.ellipse(mask, (112, 112), (75, 95), 0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (31, 31), 11)
    mask_3ch = np.stack([mask]*3, axis=2)
    
    blended = (res_a * (1.0 - alpha * mask_3ch) + res_b * (alpha * mask_3ch)).astype(np.uint8)
    return blended

def build_identity_splits():
    manip_files = [f.stem for f in MANIP_VIDEOS_DIR.glob("*.mp4")]
    pairs = [m.split("_") for m in manip_files if "_" in m]

    adj = defaultdict(set)
    for a, b in pairs:
        adj[a].add(b)
        adj[b].add(a)

    visited = set()
    clusters = []
    for node in sorted(adj.keys()):
        if node not in visited:
            comp = set()
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.add(curr)
                for nbr in adj[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)
            clusters.append(comp)

    # Separate clusters into with_real and manip_only
    with_real = []
    manip_only = []
    for c in clusters:
        has_real = any((REAL_VIDEOS_DIR / f"{x}.mp4").is_file() for x in c)
        if has_real:
            with_real.append(c)
        else:
            manip_only.append(c)

    # Deterministic cluster assignment
    # 25 clusters with real videos: 17 Train (~68%), 4 Val (~16%), 4 Test (~16%)
    # 41 manip-only clusters: 29 Train, 6 Val, 6 Test
    random.seed(42)
    random.shuffle(with_real)
    random.shuffle(manip_only)

    train_clusters = with_real[:17] + manip_only[:29]
    val_clusters = with_real[17:21] + manip_only[29:35]
    test_clusters = with_real[21:] + manip_only[35:]

    train_ids = set().union(*train_clusters)
    val_ids = set().union(*val_clusters)
    test_ids = set().union(*test_clusters)

    # Verify zero identity leakage
    assert len(train_ids.intersection(val_ids)) == 0, "Train-Val identity leak!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train-Test identity leak!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val-Test identity leak!"

    print(f"Identity Splits: Train={len(train_ids)} IDs, Val={len(val_ids)} IDs, Test={len(test_ids)} IDs")
    return train_ids, val_ids, test_ids

def extract_from_videos():
    train_ids, val_ids, test_ids = build_identity_splits()
    detector = init_yunet()

    # Create destination directories
    for split in ["train", "val", "test"]:
        for cls in ["real", "fake"]:
            (OUTPUT_DIR / split / cls).mkdir(parents=True, exist_ok=True)

    counts = {
        "train": {"real": 0, "fake": 0},
        "val": {"real": 0, "fake": 0},
        "test": {"real": 0, "fake": 0}
    }

    # 1. Extract Real Videos
    print("\n[1/3] Extracting Real Video Face Crops...")
    real_video_files = sorted(list(REAL_VIDEOS_DIR.glob("*.mp4")))
    for vpath in real_video_files:
        vid_id = vpath.stem
        if vid_id in train_ids:
            split = "train"
            target_frames = 22
        elif vid_id in val_ids:
            split = "val"
            target_frames = 18
        elif vid_id in test_ids:
            split = "test"
            target_frames = 18
        else:
            continue

        cap = cv2.VideoCapture(str(vpath))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            continue

        step = max(1, total_frames // (target_frames + 2))
        saved = 0
        for i in range(target_frames + 5):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            crop = extract_face_crop(frame, detector)
            if crop is not None:
                fname = f"real_{vid_id}_f{i:04d}.jpg"
                out_path = OUTPUT_DIR / split / "real" / fname
                cv2.imwrite(str(out_path), crop)
                saved += 1
                counts[split]["real"] += 1
                if saved >= target_frames:
                    break
        cap.release()

    # 2. Extract Manipulated / Deepfake Videos
    print("\n[2/3] Extracting Manipulated Video Face Crops...")
    manip_video_files = sorted(list(MANIP_VIDEOS_DIR.glob("*.mp4")))
    for vpath in manip_video_files:
        pair = vpath.stem.split("_")
        id_a, id_b = pair[0], pair[1]
        if id_a in train_ids or id_b in train_ids:
            split = "train"
            target_frames = 8
        elif id_a in val_ids or id_b in val_ids:
            split = "val"
            target_frames = 12
        elif id_a in test_ids or id_b in test_ids:
            split = "test"
            target_frames = 12
        else:
            continue

        cap = cv2.VideoCapture(str(vpath))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            continue

        step = max(1, total_frames // (target_frames + 2))
        saved = 0
        for i in range(target_frames + 5):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            crop = extract_face_crop(frame, detector)
            if crop is not None:
                fname = f"manip_{vpath.stem}_f{i:04d}.jpg"
                out_path = OUTPUT_DIR / split / "fake" / fname
                cv2.imwrite(str(out_path), crop)
                saved += 1
                counts[split]["fake"] += 1
                if saved >= target_frames:
                    break
        cap.release()

    # 3. Add Synthesized Facial Morphs to train and val to hit exact 1,000 / 1,000 balance
    print("\n[3/3] Generating Synthesized Facial Morphs & Blends...")
    for split in ["train", "val"]:
        real_crops = list((OUTPUT_DIR / split / "real").glob("*.jpg"))
        deficit = counts[split]["real"] - counts[split]["fake"]
        if deficit > 0 and len(real_crops) >= 2:
            print(f"  Generating {deficit} morph samples for {split}...")
            for idx in range(deficit):
                img1_path, img2_path = random.sample(real_crops, 2)
                im1 = cv2.imread(str(img1_path))
                im2 = cv2.imread(str(img2_path))
                alpha = random.uniform(0.35, 0.65)
                morph = generate_morph_sample(im1, im2, alpha=alpha)
                fname = f"morph_{split}_{idx:04d}.jpg"
                cv2.imwrite(str(OUTPUT_DIR / split / "fake" / fname), morph)
                counts[split]["fake"] += 1

    # Final tally
    total_real = sum(counts[s]["real"] for s in counts)
    total_fake = sum(counts[s]["fake"] for s in counts)

    manifest = {
        "dataset_name": "Expanded Multi-Modal Face Forensics (FF++ c23 & Facial Morphs)",
        "identity_independent": True,
        "counts": counts,
        "total_real": total_real,
        "total_fake": total_fake,
        "total_samples": total_real + total_fake,
        "splits": {
            "train": counts["train"],
            "val": counts["val"],
            "test": counts["test"]
        }
    }

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "="*60)
    print("DATASET CREATION COMPLETE")
    print(f"  Train: Real={counts['train']['real']}, Fake={counts['train']['fake']}")
    print(f"  Val:   Real={counts['val']['real']}, Fake={counts['val']['fake']}")
    print(f"  Test:  Real={counts['test']['real']}, Fake={counts['test']['fake']}")
    print(f"  TOTAL: Real={total_real}, Fake={total_fake} (Sum: {total_real+total_fake})")
    print(f"Saved manifest to {manifest_path}")
    print("="*60)

if __name__ == "__main__":
    extract_from_videos()

