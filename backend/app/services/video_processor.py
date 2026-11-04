"""
video_processor.py — Robust video frame extraction for DeepGuard AI.

Provides resilient multi-strategy frame extraction:
  1. Primary seek-based keyframe sampling for well-indexed video containers.
  2. Sequential streaming fallback for single-frame videos, unindexed containers,
     variable frame rate (VFR) streams, and mobile recordings where seeking fails.
  3. Secondary ImageIO decoder fallback if OpenCV demuxer encounters errors.
  4. Comprehensive forensic logging (dimensions, FPS, frame count, decoder).
"""

import os
import tempfile
import logging
from typing import List
import cv2
import numpy as np

from .exceptions import InvalidImageError, CorruptFileError

logger = logging.getLogger(__name__)


def extract_video_frames(file_path: str, num_frames: int = 5) -> List[str]:
    """
    Extracts up to `num_frames` representative frames from the video file and
    saves them as temporary JPEG images.

    Returns a list of paths to the temporary image files.
    The caller is responsible for cleaning up these temporary files.

    Raises:
        InvalidImageError: If the file does not exist.
        CorruptFileError: If the file is 0 bytes, invalid, corrupt, or unsupported.
    """
    if not os.path.isfile(file_path):
        raise InvalidImageError(f"Video file not found at path: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise CorruptFileError("Uploaded video file is empty (0 bytes).")

    extracted_images: List[np.ndarray] = []
    decoder_used = "opencv"

    # ── Strategy 1: OpenCV VideoCapture ──────────────────────────────────────
    cap = cv2.VideoCapture(file_path)
    if cap.isOpened():
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

            logger.info(
                "Inspecting video: path=%s, size=%d bytes, total_frames=%d, fps=%.2f, dimensions=%dx%d",
                os.path.basename(file_path), file_size, total_frames, fps, width, height,
            )

            # Strategy 1A: Seek-based extraction (if frame count is known and positive)
            if total_frames > 0:
                target_count = min(num_frames, total_frames)
                indices = np.linspace(0, total_frames - 1, num=target_count, dtype=int)
                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        extracted_images.append(frame)

            # Strategy 1B: Sequential streaming read fallback
            # (Triggered if seeking yielded 0 frames, or total_frames <= 0, or video has few frames)
            if len(extracted_images) == 0:
                logger.info(
                    "Seek-based extraction yielded 0 frames for %s; attempting sequential decoding fallback.",
                    os.path.basename(file_path),
                )
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                seq_frames = []
                # Bound maximum read frames to prevent unbounded memory usage on long videos
                max_scan_frames = 600
                while len(seq_frames) < max_scan_frames:
                    ret, frame = cap.read()
                    if not ret or frame is None or frame.size == 0:
                        break
                    seq_frames.append(frame)

                if seq_frames:
                    target_count = min(num_frames, len(seq_frames))
                    sample_indices = np.linspace(0, len(seq_frames) - 1, num=target_count, dtype=int)
                    extracted_images = [seq_frames[i] for i in sample_indices]
                    logger.info(
                        "Sequential fallback successfully read %d frames (sampled %d keyframes).",
                        len(seq_frames), len(extracted_images),
                    )

        except Exception as exc:
            logger.warning("OpenCV video decoding error on %s: %s", os.path.basename(file_path), exc)
        finally:
            cap.release()

    # ── Strategy 2: ImageIO Secondary Fallback ───────────────────────────────
    if len(extracted_images) == 0:
        try:
            import imageio
            logger.info("Attempting ImageIO fallback reader for %s", os.path.basename(file_path))
            reader = imageio.get_reader(file_path)
            iio_frames = []
            max_scan_frames = 600
            for i, frame in enumerate(reader):
                if i >= max_scan_frames:
                    break
                # ImageIO returns RGB numpy arrays, convert to BGR for uniform OpenCV saving
                bgr = cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR)
                iio_frames.append(bgr)
            reader.close()

            if iio_frames:
                decoder_used = "imageio"
                target_count = min(num_frames, len(iio_frames))
                sample_indices = np.linspace(0, len(iio_frames) - 1, num=target_count, dtype=int)
                extracted_images = [iio_frames[i] for i in sample_indices]
                logger.info("ImageIO fallback extracted %d frames.", len(extracted_images))
        except Exception as exc:
            logger.warning("ImageIO fallback failed on %s: %s", os.path.basename(file_path), exc)

    # ── Validation of Extracted Output ───────────────────────────────────────
    if not extracted_images:
        logger.error(
            "Failed to extract any valid frames from video: path=%s, size=%d bytes",
            os.path.basename(file_path), file_size,
        )
        raise CorruptFileError(
            "Failed to extract any valid frames from the video. "
            "The file may be corrupt, empty, or encoded in an unsupported format."
        )

    # ── Save extracted frames to temporary JPEG files ────────────────────────
    extracted_paths: List[str] = []
    try:
        for frame in extracted_images:
            fd, temp_path = tempfile.mkstemp(suffix=".jpg", prefix="deepguard_video_frame_")
            os.close(fd)
            # Write with high JPEG quality for forensic inference
            cv2.imwrite(temp_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            extracted_paths.append(temp_path)

        logger.info(
            "Frame extraction complete: file=%s, extracted_count=%d, decoder=%s",
            os.path.basename(file_path), len(extracted_paths), decoder_used,
        )
        return extracted_paths

    except Exception as exc:
        # Cleanup temporary files on write failure
        for p in extracted_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        raise CorruptFileError(f"Failed to persist extracted video frames: {exc}")
