"""
prepare_video_dataset.py
Extracts aligned keyframe face crops from FaceForensics++ videos with strict identity-level partitioning.
Guarantees zero identity and zero video leakage across Train, Val, and Test splits.
"""

import os
import json
import random
from pathlib import Path
from collections import defaultdict
import cv2
import numpy as np

def build_identity_splits(seed=42):
    real_dir = Path("ai/evaluation/original_c23_subset/original_sequences/youtube/c23/videos")
    fake_dir = Path("ai/evaluation/manipulated_c23_subset/manipulated_sequences/Face2Face/c23/videos")

    real_files = {f.stem: f for f in real_dir.glob("*.mp4")}
    fake_files = {f.stem: f for f in fake_dir.glob("*.mp4")}

    id_pairs = []
    graph = defaultdict(set)
    for f_stem in fake_files:
        if "_" in f_stem:
            s, t = f_stem.split("_")
            id_pairs.append((s, t, f_stem))
            graph[s].add(t)
            graph[t].add(s)

    visited = set()
    components = []
    all_ids = set(real_files.keys()) | set(graph.keys())

    for node in sorted(all_ids):
        if node not in visited:
            comp = []
            q = [node]
            visited.add(node)
            while q:
                curr = q.pop(0)
                comp.append(curr)
                for nbr in graph[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        q.append(nbr)
            components.append(sorted(comp))

    clusters_with_real = [c for c in components if any(x in real_files for x in c)]
    clusters_fake_only = [c for c in components if not any(x in real_files for x in c)]

    random.seed(seed)
    random.shuffle(clusters_with_real)
    random.shuffle(clusters_fake_only)

    # Balanced Test: 6 clusters with real (12 real vids, 12 fake vids = 24 videos)
    test_clusters = clusters_with_real[:6]
    # Balanced Val: 5 clusters with real (10 real vids, 10 fake vids = 20 videos)
    val_clusters = clusters_with_real[6:11]
    # Train gets remaining: 14 clusters with real (28 real vids) + 41 fake-only clusters (109 fake vids = 137 videos)
    train_clusters = clusters_with_real[11:] + clusters_fake_only

    splits = {"train": train_clusters, "val": val_clusters, "test": test_clusters}

    # Verify zero leakage
    c_tr = set(x for c in train_clusters for x in c)
    c_va = set(x for c in val_clusters for x in c)
    c_te = set(x for c in test_clusters for x in c)
    assert len(c_tr & c_va) == 0, "Train-Val identity leakage detected!"
    assert len(c_tr & c_te) == 0, "Train-Test identity leakage detected!"
    assert len(c_va & c_te) == 0, "Val-Test identity leakage detected!"

    video_split_map = {}
    for split_name, clusters in splits.items():
        c_ids = set(x for c in clusters for x in c)
        for r_id in c_ids:
            if r_id in real_files:
                video_split_map[r_id] = {
                    "path": str(real_files[r_id]),
                    "label": "REAL",
                    "class": 1,
                    "split": split_name,
                    "identities": [r_id]
                }
        for s, t, f_stem in id_pairs:
            if s in c_ids and t in c_ids:
                video_split_map[f_stem] = {
                    "path": str(fake_files[f_stem]),
                    "label": "FAKE",
                    "class": 0,
                    "split": split_name,
                    "identities": [s, t]
                }

    print(f"Total videos partitioned: {len(video_split_map)}")
    for sname in ["train", "val", "test"]:
        v_in_s = [v for v in video_split_map.values() if v["split"] == sname]
        reals = [v for v in v_in_s if v["label"] == "REAL"]
        fakes = [v for v in v_in_s if v["label"] == "FAKE"]
        print(f"  [{sname.upper()}] Total: {len(v_in_s)} | Reals: {len(reals)} | Fakes: {len(fakes)}")

    return video_split_map


def extract_and_align_face(frame_bgr, face_cascade):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    h, w, _ = frame_bgr.shape
    if len(faces) > 0:
        # Pick largest face
        x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        pad_x = int(0.20 * fw)
        pad_y = int(0.25 * fh)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + fw + pad_x)
        y2 = min(h, y + fh + pad_y)
        crop = frame_bgr[y1:y2, x1:x2]
        bbox = [round(x1 / w, 4), round(y1 / h, 4), round((x2 - x1) / w, 4), round((y2 - y1) / h, 4)]
    else:
        # Center square crop fallback
        side = min(h, w)
        y1 = (h - side) // 2
        x1 = (w - side) // 2
        crop = frame_bgr[y1:y1 + side, x1:x1 + side]
        bbox = [round(x1 / w, 4), round(y1 / h, 4), round(side / w, 4), round(side / h, 4)]

    aligned = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_AREA)
    return aligned, bbox


def main():
    face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    out_base = Path("ai/datasets/video_benchmark")
    out_base.mkdir(parents=True, exist_ok=True)

    video_split_map = build_identity_splits(seed=42)
    manifest = []

    print("\n--> Extracting 12 keyframes per video...")
    total_extracted = 0

    for vid_idx, (vid_stem, meta) in enumerate(sorted(video_split_map.items())):
        vid_path = meta["path"]
        split = meta["split"]
        label = meta["label"]
        class_idx = meta["class"]

        split_dir = out_base / split / label.lower()
        split_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(vid_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            cap.release()
            continue

        num_samples = 12
        step = max(1, total_frames // num_samples)
        frame_indices = [min(i * step, total_frames - 1) for i in range(num_samples)]

        for f_order, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            crop_224, bbox = extract_and_align_face(frame, face_cascade)
            out_fname = f"{vid_stem}_f{f_order:02d}_{frame_idx:05d}.jpg"
            out_fpath = split_dir / out_fname
            cv2.imwrite(str(out_fpath), crop_224)

            timestamp_sec = round(frame_idx / fps, 3)
            manifest.append({
                "video_name": vid_stem,
                "split": split,
                "label": label,
                "class": class_idx,
                "frame_order": f_order,
                "frame_index": frame_idx,
                "timestamp_seconds": timestamp_sec,
                "bbox": bbox,
                "rel_path": str(out_fpath.relative_to(out_base)).replace("\\", "/")
            })
            total_extracted += 1

        cap.release()
        if (vid_idx + 1) % 30 == 0 or (vid_idx + 1) == len(video_split_map):
            print(f"  Processed {vid_idx + 1}/{len(video_split_map)} videos ({total_extracted} frames extracted)")

    manifest_path = out_base / "dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "total_videos": len(video_split_map),
            "total_frames": len(manifest),
            "videos": video_split_map,
            "frames": manifest
        }, f, indent=2)

    print(f"\nExtraction complete! Saved manifest to {manifest_path}")

if __name__ == "__main__":
    main()

