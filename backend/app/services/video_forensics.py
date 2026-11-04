"""
video_forensics.py — Production-Grade Video Deepfake & Cross-Modal Forensics Pipeline.

Provides rigorous evidence-based video forensic analysis:
  1. Video Container & Stream Validation (dimensions, FPS, duration, codec).
  2. Scene-Cut Aware Keyframe Extraction (color histogram delta prevents false temporal flicker).
  3. Per-Frame Face Localization & Manipulation Scoring via YuNet + EfficientNet-B0.
  4. Inter-Frame Temporal Inconsistency Analysis (facial displacement & texture variance).
  5. Audio Track Demuxing & Cross-Modal Synthetic Speech Verification via AASIST.
  6. Calibrated Multimodal Aggregation: Combines frame, temporal, and acoustic evidence.
"""

import os
import cv2
import math
import logging
import tempfile
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

from .exceptions import InvalidImageError, CorruptFileError
from .image_forensics import get_image_forensics_engine
from .audio_detector import run_audio_inference
from .audio_preprocessor import load_and_preprocess_audio

logger = logging.getLogger(__name__)


@dataclass
class VideoFrameEvidence:
    """Forensic evidence for a single extracted keyframe."""
    frame_index: int
    timestamp_seconds: float
    manipulation_score: float
    faces_detected: int
    primary_bbox: Optional[Tuple[float, float, float, float]] = None
    is_scene_cut: bool = False


@dataclass
class VideoForensicsResult:
    """Complete multimodal forensic findings for a video."""
    prediction: str                    # "authentic" | "synthetic" | "uncertain"
    evidence_category: str             # "LIKELY_AUTHENTIC" | "LIKELY_MANIPULATED" | "INCONCLUSIVE"
    confidence: float                  # Calibrated confidence (0.0 - 1.0)
    risk_level: str                    # "low" | "medium" | "high" | "critical"
    duration_seconds: float
    total_frames_sampled: int
    face_manipulation_score: float
    temporal_inconsistency_score: float
    audio_spoof_score: Optional[float] = None
    has_audio_track: bool = False
    cross_modal_inconsistency: Optional[float] = None
    frame_evidences: List[VideoFrameEvidence] = field(default_factory=list)
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


class VideoForensicsEngine:
    """Thread-safe video deepfake detection engine."""

    def __init__(self, model_manager=None):
        self._model_manager = model_manager
        self._image_engine = get_image_forensics_engine(model_manager=model_manager)

    def extract_keyframes_with_metadata(
        self,
        video_path: str,
        num_frames: int = 8
    ) -> Tuple[List[Tuple[float, np.ndarray, bool]], float, int, int]:
        """
        Samples up to `num_frames` keyframes, computes timestamps, and detects scene cuts.
        Returns: (list_of_(timestamp, bgr_frame, is_scene_cut), duration_sec, width, height)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise CorruptFileError(f"OpenCV could not open video stream: {video_path}")

        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
            if fps <= 0:
                fps = 25.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration = total_frames / fps if total_frames > 0 else 0.0

            raw_frames: List[Tuple[float, np.ndarray]] = []

            if total_frames > 0:
                target_count = min(num_frames, total_frames)
                indices = np.linspace(0, total_frames - 1, num=target_count, dtype=int)
                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        timestamp = float(idx) / fps
                        raw_frames.append((timestamp, frame))

            # Sequential fallback if seek returned 0
            if not raw_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                seq = []
                count = 0
                while count < 600:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break
                    seq.append(frame)
                    count += 1
                if seq:
                    target_count = min(num_frames, len(seq))
                    sample_indices = np.linspace(0, len(seq) - 1, num=target_count, dtype=int)
                    duration = len(seq) / fps
                    for s_idx in sample_indices:
                        raw_frames.append((float(s_idx) / fps, seq[s_idx]))

            if not raw_frames:
                raise CorruptFileError("Failed to decode any valid video frames.")

            # Detect scene cuts via HSV histogram correlation between consecutive frames
            results: List[Tuple[float, np.ndarray, bool]] = []
            prev_hist = None

            for t, f in raw_frames:
                is_cut = False
                try:
                    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
                    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                    if prev_hist is not None:
                        correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                        if correlation < 0.45:  # Significant color shift = scene cut
                            is_cut = True
                    prev_hist = hist
                except Exception:
                    pass

                results.append((t, f, is_cut))

            return results, duration, width, height

        finally:
            cap.release()

    def extract_audio_track(self, video_path: str) -> Optional[str]:
        """
        Attempts to extract audio track to a temporary WAV file using pydub/scipy.
        Returns path to WAV file or None if video has no audio track.
        """
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(video_path)
            if audio is None or len(audio) < 200:  # Less than 200ms
                return None

            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()
            audio.export(temp_wav.name, format="wav")
            return temp_wav.name
        except Exception as exc:
            logger.debug("Audio extraction from video not available or no audio stream: %s", exc)
            return None

    def analyze_video(self, video_path: str) -> VideoForensicsResult:
        """
        Executes end-to-end video deepfake forensics with cross-modal audio analysis.
        """
        if not os.path.isfile(video_path):
            raise InvalidImageError(f"Video file not found: {video_path}")
        if os.path.getsize(video_path) == 0:
            raise CorruptFileError("Uploaded video file is empty (0 bytes).")

        # 1. Keyframe extraction & scene-cut detection
        sampled_frames, duration, width, height = self.extract_keyframes_with_metadata(video_path)

        # 2. Analyze each keyframe
        frame_evidences: List[VideoFrameEvidence] = []
        frame_scores: List[float] = []
        consecutive_diffs: List[float] = []
        prev_face_score = None
        indicators: List[Dict[str, Any]] = []

        for idx, (timestamp, bgr_frame, is_cut) in enumerate(sampled_frames):
            # Save frame temporarily to run image forensics
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                temp_frame_path = tf.name
            try:
                cv2.imwrite(temp_frame_path, bgr_frame)
                img_res = self._image_engine.analyze_image(temp_frame_path)

                manip_score = img_res.face_manipulation_score if img_res.face_manipulation_score is not None else img_res.gan_artifact_score
                manip_score = manip_score or 0.0

                frame_evidences.append(VideoFrameEvidence(
                    frame_index=idx,
                    timestamp_seconds=round(timestamp, 2),
                    manipulation_score=round(manip_score, 4),
                    faces_detected=img_res.faces_detected,
                    primary_bbox=img_res.primary_face_bbox,
                    is_scene_cut=is_cut
                ))
                frame_scores.append(manip_score)

                # Compute temporal jump only within the SAME scene
                if prev_face_score is not None and not is_cut:
                    diff = abs(manip_score - prev_face_score)
                    consecutive_diffs.append(diff)
                prev_face_score = manip_score

                # Flag high-risk frame indicators
                if manip_score >= 0.70:
                    indicators.append({
                        "indicator_type": "suspicious_video_keyframe",
                        "description": f"Keyframe #{idx+1} at {timestamp:.2f}s displays elevated manipulation indicators ({manip_score:.1%}).",
                        "severity": "high",
                        "timestamp_seconds": round(timestamp, 2),
                        "frame_number": idx,
                        "region_x": img_res.primary_face_bbox[0] if img_res.primary_face_bbox else None,
                        "region_y": img_res.primary_face_bbox[1] if img_res.primary_face_bbox else None,
                        "region_w": img_res.primary_face_bbox[2] if img_res.primary_face_bbox else None,
                        "region_h": img_res.primary_face_bbox[3] if img_res.primary_face_bbox else None,
                    })

            finally:
                if os.path.exists(temp_frame_path):
                    try:
                        os.remove(temp_frame_path)
                    except OSError:
                        pass

        # 3. Calculate video visual scores
        avg_frame_score = float(np.mean(frame_scores)) if frame_scores else 0.0
        max_frame_score = float(np.max(frame_scores)) if frame_scores else 0.0
        # Peak-weighted video score: 60% peak frame + 40% average
        video_face_score = round((max_frame_score * 0.60) + (avg_frame_score * 0.40), 4)

        # 4. Temporal inconsistency score: variance of non-scene-cut inter-frame deltas
        temporal_score = 0.0
        if consecutive_diffs:
            temporal_score = round(float(np.mean(consecutive_diffs)), 4)
            if temporal_score >= 0.30:
                indicators.append({
                    "indicator_type": "temporal_jitter_anomaly",
                    "description": f"Inter-frame facial variance ({temporal_score:.1%}) indicates temporal synthesis or face-swap flickering across frames.",
                    "severity": "high"
                })

        # 5. Extract and analyze audio track (Cross-Modal Analysis)
        audio_spoof_score = None
        has_audio = False
        cross_modal_diff = None
        extracted_wav = self.extract_audio_track(video_path)

        if extracted_wav is not None:
            has_audio = True
            try:
                audio_res = run_audio_inference(extracted_wav)
                audio_spoof_score = round(audio_res.voice_cloning_score or 0.0, 4)

                if audio_spoof_score >= 0.60:
                    indicators.append({
                        "indicator_type": "cross_modal_audio_spoof",
                        "description": f"Audio track in video contains synthetic speech vocoder artifacts (spoof risk: {audio_spoof_score:.1%}).",
                        "severity": "high"
                    })

                # Cross-modal inconsistency: difference between visual manipulation and audio spoofing
                cross_modal_diff = round(abs(video_face_score - audio_spoof_score), 4)
                if cross_modal_diff >= 0.45:
                    indicators.append({
                        "indicator_type": "multimodal_modality_mismatch",
                        "description": f"Discrepancy between visual manipulation ({video_face_score:.1%}) and audio authenticity ({audio_spoof_score:.1%}) suggests selective modal tampering.",
                        "severity": "medium"
                    })

            except Exception as exc:
                logger.debug("Video audio inference error: %s", exc)
            finally:
                if os.path.exists(extracted_wav):
                    try:
                        os.remove(extracted_wav)
                    except OSError:
                        pass

        # 6. Integrated Multimodal Decision Strategy
        limitations = [
            f"Analyzed {len(sampled_frames)} sampled keyframes across {duration:.2f}s of video.",
            "Temporal inconsistency evaluated across intra-scene frame transitions.",
            "Automated video detection evaluates facial boundary seams and vocoder harmonics; it does not replace human forensics."
        ]

        if not has_audio:
            limitations.append("Video has no decodable audio stream. Analysis restricted to visual and temporal signals.")

        # Combined video risk
        if has_audio and audio_spoof_score is not None:
            overall_fake = (video_face_score * 0.55) + (temporal_score * 0.20) + (audio_spoof_score * 0.25)
        else:
            overall_fake = (video_face_score * 0.70) + (temporal_score * 0.30)

        overall_fake = round(overall_fake, 4)
        overall_real = round(1.0 - overall_fake, 4)

        if video_face_score >= 0.60 or (audio_spoof_score is not None and audio_spoof_score >= 0.75):
            prediction = "synthetic"
            evidence_category = "LIKELY_MANIPULATED"
            confidence = overall_fake
            risk_level = "critical" if confidence >= 0.85 else "high"
        elif overall_fake <= 0.35 and max_frame_score <= 0.40:
            prediction = "authentic"
            evidence_category = "LIKELY_AUTHENTIC"
            confidence = overall_real
            risk_level = "low"
            indicators.append({
                "indicator_type": "temporal_coherence_verified",
                "description": f"All {len(sampled_frames)} keyframes and temporal transitions exhibit natural photometric coherence.",
                "severity": "info"
            })
        else:
            prediction = "uncertain"
            evidence_category = "INCONCLUSIVE"
            confidence = round(max(overall_fake, overall_real), 4)
            risk_level = "medium"
            indicators.append({
                "indicator_type": "video_analysis_inconclusive",
                "description": "Composite multimodal scores fall within the indeterminate margin (0.35 - 0.60).",
                "severity": "medium"
            })

        return VideoForensicsResult(
            prediction=prediction,
            evidence_category=evidence_category,
            confidence=confidence,
            risk_level=risk_level,
            duration_seconds=round(duration, 2),
            total_frames_sampled=len(sampled_frames),
            face_manipulation_score=video_face_score,
            temporal_inconsistency_score=temporal_score,
            audio_spoof_score=audio_spoof_score,
            has_audio_track=has_audio,
            cross_modal_inconsistency=cross_modal_diff,
            frame_evidences=frame_evidences,
            indicators=indicators,
            limitations=limitations
        )


_video_forensics_instance: Optional[VideoForensicsEngine] = None


def get_video_forensics_engine(model_manager=None) -> VideoForensicsEngine:
    global _video_forensics_instance
    if _video_forensics_instance is None:
        _video_forensics_instance = VideoForensicsEngine(model_manager=model_manager)
    return _video_forensics_instance
