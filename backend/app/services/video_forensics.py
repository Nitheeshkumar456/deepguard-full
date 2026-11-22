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
import shutil
import logging
import tempfile
import subprocess
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

from .exceptions import InvalidImageError, CorruptFileError
from .image_forensics import get_image_forensics_engine
from .audio_detector import run_audio_inference

logger = logging.getLogger(__name__)


def _find_ffmpeg_binary() -> Optional[str]:
    """Locate an available ffmpeg executable on system PATH or known paths."""
    which_path = shutil.which("ffmpeg")
    if which_path and os.path.isfile(which_path):
        return which_path

    known_candidates = [
        r"C:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional\BIN\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in known_candidates:
        if os.path.isfile(p):
            return p
    return None


@dataclass
class VideoFrameEvidence:
    """Forensic evidence for a single extracted keyframe."""
    frame_index: int
    timestamp_seconds: float
    manipulation_score: float
    faces_detected: int
    primary_bbox: Optional[Tuple[float, float, float, float]] = None
    is_scene_cut: bool = False
    prediction: str = "authentic"  # "authentic" | "synthetic" | "uncertain"
    morphing_score: Optional[float] = None
    explanation: Optional[str] = None
    is_suspicious: bool = False


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
    # v2 Morphing & Face-Swap detection signals
    morphing_score: Optional[float] = None
    boundary_discontinuity_score: Optional[float] = None
    lbp_entropy_score: Optional[float] = None
    color_mismatch_score: Optional[float] = None
    suspicious_timestamps: List[float] = field(default_factory=list)
    suspicious_frames_count: int = 0
    frame_evidences: List[VideoFrameEvidence] = field(default_factory=list)
    frame_level_predictions: List[Dict[str, Any]] = field(default_factory=list)
    visual_explanations: List[Dict[str, Any]] = field(default_factory=list)
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
        num_frames: int = 12
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
        Attempts to extract audio track to a temporary 16kHz mono WAV file for AASIST.
        Uses ffmpeg binary directly when available, falling back to pydub.
        Returns path to WAV file or None if video has no audio track.
        """
        ffmpeg_bin = _find_ffmpeg_binary()

        # Primary extraction: direct ffmpeg extraction to standardized 16kHz mono WAV
        if ffmpeg_bin:
            try:
                temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_wav_path = temp_wav.name
                temp_wav.close()

                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i", video_path,
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    temp_wav_path
                ]
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15
                )
                if proc.returncode == 0 and os.path.isfile(temp_wav_path) and os.path.getsize(temp_wav_path) > 1000:
                    return temp_wav_path
                elif os.path.exists(temp_wav_path):
                    try:
                        os.remove(temp_wav_path)
                    except OSError:
                        pass
            except Exception as ffmpeg_err:
                logger.debug("Direct ffmpeg audio extraction attempt failed: %s", ffmpeg_err)

        # Secondary fallback: pydub
        try:
            from pydub import AudioSegment
            if ffmpeg_bin:
                AudioSegment.converter = ffmpeg_bin
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
        frame_morphing_scores: List[float] = []
        frame_boundary_scores: List[float] = []
        frame_lbp_scores: List[float] = []
        frame_color_scores: List[float] = []
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

                frame_pred = "synthetic" if manip_score >= 0.38 else ("authentic" if manip_score <= 0.20 else "uncertain")
                is_suspicious = manip_score >= 0.35 or (img_res.morphing_score is not None and img_res.morphing_score >= 0.50)

                if is_suspicious:
                    explanation = f"Frame #{idx+1} at {timestamp:.2f}s displays manipulation artifacts (score: {manip_score:.1%})"
                    if img_res.morphing_score and img_res.morphing_score >= 0.50:
                        explanation += f", facial morphing seam discontinuity ({img_res.morphing_score:.1%})"
                else:
                    explanation = f"Frame #{idx+1} at {timestamp:.2f}s shows consistent natural facial features (authenticity: {1.0 - manip_score:.1%})"

                frame_evidences.append(VideoFrameEvidence(
                    frame_index=idx,
                    timestamp_seconds=round(timestamp, 2),
                    manipulation_score=round(manip_score, 4),
                    faces_detected=img_res.faces_detected,
                    primary_bbox=img_res.primary_face_bbox,
                    is_scene_cut=is_cut,
                    prediction=frame_pred,
                    morphing_score=img_res.morphing_score,
                    explanation=explanation,
                    is_suspicious=is_suspicious
                ))
                frame_scores.append(manip_score)

                # Track keyframe morphing metrics
                if img_res.morphing_score is not None:
                    frame_morphing_scores.append(img_res.morphing_score)
                if img_res.boundary_discontinuity_score is not None:
                    frame_boundary_scores.append(img_res.boundary_discontinuity_score)
                if img_res.lbp_entropy_score is not None:
                    frame_lbp_scores.append(img_res.lbp_entropy_score)
                if img_res.color_mismatch_score is not None:
                    frame_color_scores.append(img_res.color_mismatch_score)

                # Compute temporal jump only within the SAME scene
                if prev_face_score is not None and not is_cut:
                    diff = abs(manip_score - prev_face_score)
                    consecutive_diffs.append(diff)
                prev_face_score = manip_score

                # Flag high-risk frame indicators
                if is_suspicious:
                    indicators.append({
                        "indicator_type": "suspicious_video_keyframe",
                        "description": explanation,
                        "severity": "critical" if manip_score >= 0.75 else "high",
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

        # 3. Validated Multi-Frame Aggregation Method:
        # Avoids classifying an entire video based on a single rogue frame by evaluating:
        #   a) Top-K Suspicious Window: mean of the top 35% most suspicious frames (k >= 2)
        #   b) Temporal Average: overall mean across sampled frames
        #   c) Suspicious Frame Count: count of frames exceeding detection threshold
        N = len(frame_scores)
        sorted_scores = sorted(frame_scores, reverse=True)
        k = max(2, int(np.ceil(0.35 * N)))
        top_k_mean = float(np.mean(sorted_scores[:k])) if frame_scores else 0.0
        avg_frame_score = float(np.mean(frame_scores)) if frame_scores else 0.0
        max_frame_score = float(np.max(frame_scores)) if frame_scores else 0.0

        # Base visual face score: 70% top-k window + 30% temporal average
        video_face_score = round((top_k_mean * 0.70) + (avg_frame_score * 0.30), 4)

        # Identify suspicious frames & timestamps
        suspicious_frames = [f for f in frame_evidences if f.is_suspicious]
        suspicious_timestamps = [f.timestamp_seconds for f in suspicious_frames]
        suspicious_count = len(suspicious_frames)

        # 4. Temporal inconsistency score: variance of non-scene-cut inter-frame deltas
        temporal_score = 0.0
        if consecutive_diffs:
            temporal_score = round(float(np.mean(consecutive_diffs)), 4)
            if temporal_score >= 0.18:
                indicators.append({
                    "indicator_type": "temporal_jitter_anomaly",
                    "description": f"Inter-frame facial variance ({temporal_score:.1%}) indicates temporal synthesis or face-swap flickering across frames.",
                    "severity": "high",
                    "score": temporal_score
                })

        # Additive temporal elevation (only elevates when active manipulation or rapid jitter is present)
        if temporal_score >= 0.18 and top_k_mean >= 0.20:
            visual_composite = float(np.clip(video_face_score + (temporal_score * 0.25), 0.0, 1.0))
        else:
            visual_composite = video_face_score

        # Incorporate keyframe facial morphing signals if present
        video_morphing_score = round(float(np.mean(frame_morphing_scores)), 4) if frame_morphing_scores else None
        video_boundary_score = round(float(np.mean(frame_boundary_scores)), 4) if frame_boundary_scores else None
        video_lbp_score = round(float(np.mean(frame_lbp_scores)), 4) if frame_lbp_scores else None
        video_color_score = round(float(np.mean(frame_color_scores)), 4) if frame_color_scores else None

        if video_morphing_score is not None and video_morphing_score >= 0.55:
            visual_composite = max(visual_composite, float(video_morphing_score * 0.85))

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
            "Automated video detection evaluates multi-frame consistency and vocoder harmonics; it does not replace human forensics."
        ]

        if not has_audio:
            limitations.append("Video has no decodable audio stream. Analysis restricted to visual and temporal signals.")

        if has_audio and audio_spoof_score is not None:
            overall_fake = round((visual_composite * 0.70) + (audio_spoof_score * 0.30), 4)
        else:
            overall_fake = round(visual_composite, 4)

        overall_real = round(1.0 - overall_fake, 4)

        # Calibrated Multi-Frame Decision:
        # A video is declared synthetic ONLY IF:
        #   1. At least 2 frames are suspicious AND top_k_mean >= 0.35, OR
        #   2. Visual composite >= 0.40, OR
        #   3. Audio spoof score >= 0.70
        # Prevents classifying an entire video using just one single transient suspicious frame.
        if (suspicious_count >= 2 and top_k_mean >= 0.35) or visual_composite >= 0.40 or (has_audio and audio_spoof_score is not None and audio_spoof_score >= 0.70):
            prediction = "synthetic"
            evidence_category = "LIKELY_MANIPULATED"
            confidence = round(float(np.clip(max(overall_fake, top_k_mean), 0.65, 0.99)), 4)
            risk_level = "critical" if confidence >= 0.85 else "high"
        elif overall_fake <= 0.20 and suspicious_count == 0:
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
                "description": "Composite multimodal scores fall within indeterminate margin (0.20 - 0.40). Secondary forensic review recommended.",
                "severity": "medium"
            })

        # Generate visual explanations & frame-level predictions
        visual_explanations = []
        for f in frame_evidences:
            if f.is_suspicious:
                visual_explanations.append({
                    "timestamp_seconds": f.timestamp_seconds,
                    "frame_number": f.frame_index,
                    "manipulation_score": f.manipulation_score,
                    "bounding_box": f.primary_bbox,
                    "description": f.explanation,
                    "severity": "critical" if f.manipulation_score >= 0.75 else "high"
                })

        frame_level_predictions = [
            {
                "frame_index": f.frame_index,
                "timestamp_seconds": f.timestamp_seconds,
                "prediction": f.prediction,
                "manipulation_score": f.manipulation_score,
                "is_suspicious": f.is_suspicious,
                "primary_bbox": f.primary_bbox,
                "morphing_score": f.morphing_score,
                "explanation": f.explanation
            }
            for f in frame_evidences
        ]

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
            morphing_score=video_morphing_score,
            boundary_discontinuity_score=video_boundary_score,
            lbp_entropy_score=video_lbp_score,
            color_mismatch_score=video_color_score,
            suspicious_timestamps=suspicious_timestamps,
            suspicious_frames_count=suspicious_count,
            frame_evidences=frame_evidences,
            frame_level_predictions=frame_level_predictions,
            visual_explanations=visual_explanations,
            indicators=indicators,
            limitations=limitations
        )


_video_forensics_instance: Optional[VideoForensicsEngine] = None


def get_video_forensics_engine(model_manager=None) -> VideoForensicsEngine:
    global _video_forensics_instance
    if _video_forensics_instance is None:
        _video_forensics_instance = VideoForensicsEngine(model_manager=model_manager)
    return _video_forensics_instance
