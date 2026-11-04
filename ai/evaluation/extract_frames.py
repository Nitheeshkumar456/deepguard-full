import cv2
import os
import csv
import hashlib
from pathlib import Path

# Paths
videos_dir = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/original_c23_subset/original_sequences/youtube/c23/videos")
output_dir = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/real")
manifest_path = Path(r"c:/Final_year_projects/DeepGaurd AI-Multimodel Authenticity Platfrom/DeepGuard-AI/ai/evaluation/results/real_manifest.csv")

output_dir.mkdir(parents=True, exist_ok=True)
manifest_path.parent.mkdir(parents=True, exist_ok=True)

with open(manifest_path, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["filename", "label", "sha256", "size_bytes"])

    for video_path in sorted(videos_dir.iterdir()):
        if video_path.suffix.lower() != ".mp4":
            continue
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Cannot open video {video_path.name}, skipping.")
            continue
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            print(f"Video {video_path.name} has zero frames, skipping.")
            cap.release()
            continue
        # Choose middle frame (deterministic)
        target_frame = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to read frame from {video_path.name}, skipping.")
            cap.release()
            continue
        # Save as JPEG
        image_name = video_path.stem + ".jpg"
        image_path = output_dir / image_name
        cv2.imwrite(str(image_path), frame)
        # Compute SHA256
        sha256_hash = hashlib.sha256()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        hash_hex = sha256_hash.hexdigest()
        size_bytes = image_path.stat().st_size
        writer.writerow([image_name, "real", hash_hex, size_bytes])
        cap.release()
        print(f"Extracted {image_name} from {video_path.name}")

print("Extraction complete. Manifest written to", manifest_path)
