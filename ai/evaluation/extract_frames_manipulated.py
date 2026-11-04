import cv2
import os
import csv
import hashlib
from pathlib import Path

# Paths
videos_dir = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/manipulated_c23_subset/manipulated_sequences/Face2Face/c23/videos")
output_dir = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/manipulated")
output_dir.mkdir(parents=True, exist_ok=True)

manifest_path = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/results/manipulated_manifest.csv")

with open(manifest_path, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["filename", "label", "sha256", "size_bytes"])
    for video_path in sorted(videos_dir.glob("*.mp4"))[:50]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Cannot open video {video_path}")
            continue
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        middle_frame_idx = total_frames // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print(f"Failed to read frame from {video_path}")
            continue
        img_name = video_path.stem + ".jpg"
        img_path = output_dir / img_name
        cv2.imwrite(str(img_path), frame)
        # Compute SHA256
        sha256 = hashlib.sha256()
        with open(img_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        size_bytes = img_path.stat().st_size
        writer.writerow([img_name, "fake", sha256.hexdigest(), size_bytes])
        print(f"Extracted {img_name}")
print("Extraction complete.")
