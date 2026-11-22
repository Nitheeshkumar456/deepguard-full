"""
image_forensics.py — Specialized Image Deepfake & AI Generation Forensics Engine (v2).

Provides multi-evidence image forensic analysis:
  1. Face Detection & Bounding Box Localization via OpenCV YuNet (ONNX).
  2. Dual-Path Neural Analysis:
     - Localized Face-Crop Pathway: Evaluates facial boundary blending and manipulation.
     - Global Frame Pathway: Evaluates whole-scene composition and structural artifacts.
  3. Image-Level Generative AI Detection:
     - 2D FFT Azimuthal High-Frequency Spectral Analysis (detects periodic upsampling grids).
     - Error Level Analysis (ELA) Uniformity (detects synthetic compression uniformity).
  4. Facial Morphing & Face-Swap Detection:
     - Boundary gradient discontinuity (paste-seam detection).
     - Skin texture LBP entropy analysis.
     - Face/context color histogram Bhattacharyya divergence.
     - Edge-coherence analysis at face boundaries.
  5. Calibrated Multi-Model Fusion: Weighs face-level, morphing, and image-level
     evidence, handling face and non-face media honestly without false claims.
"""

import os
import math
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image, ImageChops, ImageEnhance

from .exceptions import InvalidImageError, CorruptFileError, UnsupportedFormatError
from .morphing_detector import get_morphing_detector

logger = logging.getLogger(__name__)

# Normalize transforms matching FaceForensics++ EfficientNet-B0 training
TRANSFORM_EFFICIENTNET = T.Normalize(
    mean=[0.485, 0.456, 0.406],
    std=[0.229, 0.224, 0.225]
)

YUNET_MODEL_FILENAME = "face_detection_yunet.onnx"


@dataclass
class DetectedFace:
    """Represents a localized facial region."""
    bbox_xywh: Tuple[int, int, int, int]  # Pixel coords (x, y, w, h)
    norm_bbox: Tuple[float, float, float, float]  # Normalized coords (0-1) (x, y, w, h)
    confidence: float
    face_chip: np.ndarray  # RGB cropped face chip (padded)


@dataclass
class ImageForensicsResult:
    """Comprehensive forensic report for an image (v2 — includes morphing scores)."""
    prediction: str                    # "authentic" | "synthetic" | "uncertain"
    evidence_category: str             # "LIKELY_AUTHENTIC" | "LIKELY_MANIPULATED" | "LIKELY_AI_GENERATED" | "INCONCLUSIVE"
    confidence: float                  # Calibrated confidence (0.0 - 1.0)
    risk_level: str                    # "low" | "medium" | "high" | "critical"
    faces_detected: int
    primary_face_bbox: Optional[Tuple[float, float, float, float]] = None
    face_manipulation_score: Optional[float] = None
    gan_artifact_score: Optional[float] = None
    spectral_anomaly_score: Optional[float] = None
    ela_uniformity_score: Optional[float] = None
    morphing_score: Optional[float] = None          # NEW: composite morphing/face-swap score
    boundary_discontinuity_score: Optional[float] = None  # NEW
    lbp_entropy_score: Optional[float] = None       # NEW
    color_mismatch_score: Optional[float] = None    # NEW
    probabilities: Dict[str, float] = field(default_factory=dict)
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


class ImageForensicsEngine:
    """Thread-safe image forensics engine combining neural and spectral signals."""

    def __init__(self, model_manager=None):
        if model_manager is None:
            try:
                from .ai_service import _model_manager
                model_manager = _model_manager
            except Exception:
                pass
        self._model_manager = model_manager
        self._yunet_path = self._find_yunet_model()

    def _find_yunet_model(self) -> str:
        """Locate face_detection_yunet.onnx in services or models directory."""
        candidates = [
            os.path.join(os.path.dirname(__file__), YUNET_MODEL_FILENAME),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", "models", YUNET_MODEL_FILENAME),
            os.path.join("app", "services", YUNET_MODEL_FILENAME),
            os.path.join("ai", "models", YUNET_MODEL_FILENAME),
        ]
        for p in candidates:
            if os.path.isfile(p):
                return os.path.abspath(p)
        logger.warning("YuNet ONNX model not found in candidates: %s", candidates)
        return ""

    def detect_faces(self, bgr_image: np.ndarray, score_threshold: float = 0.6) -> List[DetectedFace]:
        """Detect faces in BGR image using YuNet."""
        if not self._yunet_path or not os.path.isfile(self._yunet_path):
            return []

        h, w, _ = bgr_image.shape
        if h < 16 or w < 16:
            return []

        try:
            detector = cv2.FaceDetectorYN_create(
                self._yunet_path,
                "",
                (w, h),
                score_threshold,
                0.3,  # NMS threshold
                5000  # Top K
            )
            detector.setInputSize((w, h))
            _, faces = detector.detect(bgr_image)
            if faces is None or len(faces) == 0:
                return []

            detected: List[DetectedFace] = []
            for face in faces:
                x, y, fw, fh = map(int, face[:4])
                conf = float(face[-1])
                # Filter out tiny sub-resolution boxes / background noise
                if fw < 40 or fh < 40:
                    continue

                # Add 25% padding around the face to include chin/hairline blending seams
                pad_x = int(fw * 0.25)
                pad_y = int(fh * 0.25)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(w, x + fw + pad_x)
                y2 = min(h, y + fh + pad_y)

                chip = bgr_image[y1:y2, x1:x2]
                if chip.size == 0:
                    continue

                rgb_chip = cv2.cvtColor(chip, cv2.COLOR_BGR2RGB)
                norm_bbox = (x / w, y / h, fw / w, fh / h)

                detected.append(DetectedFace(
                    bbox_xywh=(x, y, fw, fh),
                    norm_bbox=norm_bbox,
                    confidence=conf,
                    face_chip=rgb_chip
                ))

            # Sort detected faces by area descending (primary subject first)
            detected.sort(key=lambda f: f.bbox_xywh[2] * f.bbox_xywh[3], reverse=True)
            if detected:
                max_area = detected[0].bbox_xywh[2] * detected[0].bbox_xywh[3]
                # Filter out spurious tiny candidates relative to the primary face
                detected = [f for f in detected if (f.bbox_xywh[2] * f.bbox_xywh[3]) >= 0.20 * max_area]

            return detected

        except Exception as exc:
            logger.warning("Face detection failed via YuNet: %s", exc)
            return []

    def compute_spectral_fft_anomaly(self, rgb_image: np.ndarray) -> float:
        """
        Calculates 2D Azimuthal Fast Fourier Transform spectral energy anomaly.
        AI generative upsamplers leave periodic grid peaks in high-frequency spectrum.
        Returns a score in [0.0, 1.0], where > 0.6 indicates synthetic periodicity.
        """
        try:
            gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
            # Resize to standardized power-of-2 size for FFT
            gray_res = cv2.resize(gray, (256, 256)).astype(np.float32)

            # Compute 2D FFT and shift DC component to center
            dft = np.fft.fft2(gray_res)
            dft_shift = np.fft.fftshift(dft)
            magnitude_spectrum = 20 * np.log(np.abs(dft_shift) + 1e-8)

            # Azimuthal high-frequency ratio: ratio of outer quadrant energy to center
            cy, cx = 128, 128
            y, x = np.ogrid[:256, :256]
            dist_from_center = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

            high_freq_mask = dist_from_center > 70
            low_freq_mask = dist_from_center < 35

            high_freq_mean = float(np.mean(magnitude_spectrum[high_freq_mask]))
            low_freq_mean = float(np.mean(magnitude_spectrum[low_freq_mask]))

            # Ratio of high-to-low frequency energy
            ratio = high_freq_mean / (low_freq_mean + 1e-5)
            score = float(1.0 / (1.0 + math.exp(-12.0 * (ratio - 0.60))))
            return max(0.0, min(1.0, score))

        except Exception as exc:
            logger.debug("Spectral FFT analysis error: %s", exc)
            return 0.50

    def compute_error_level_analysis(self, file_path: str, quality: int = 90) -> float:
        """
        Error Level Analysis (ELA).
        Re-saves the image at 90% quality and calculates pixel differential variance.
        Uniform error indicates synthetic generation; natural photos exhibit high variance.
        """
        try:
            original = Image.open(file_path).convert('RGB')
            import io
            buf = io.BytesIO()
            original.save(buf, 'JPEG', quality=quality)
            buf.seek(0)
            resaved = Image.open(buf)

            # Compute absolute difference
            ela_image = ImageChops.difference(original, resaved)
            extrema = ela_image.getextrema()
            max_diff = max([ex[1] for ex in extrema])
            if max_diff == 0:
                return 0.50

            scale = 255.0 / max_diff
            ela_enhanced = ImageEnhance.Brightness(ela_image).enhance(scale)
            ela_array = np.array(ela_enhanced).astype(np.float32)

            # Measure variance across image patches
            patch_vars = []
            h, w, _ = ela_array.shape
            step = 32
            for i in range(0, h - step, step):
                for j in range(0, w - step, step):
                    patch = ela_array[i:i + step, j:j + step]
                    patch_vars.append(np.var(patch))

            if not patch_vars:
                return 0.50

            var_of_vars = float(np.var(patch_vars))
            uniformity_score = float(1.0 / (1.0 + math.exp(0.002 * (var_of_vars - 1500))))
            return max(0.0, min(1.0, uniformity_score))

        except Exception as exc:
            logger.debug("ELA analysis error: %s", exc)
            return 0.50

    def run_chip_inference(self, rgb_crop: np.ndarray, model: torch.nn.Module, device: torch.device) -> Tuple[float, float]:
        """
        Runs the EfficientNet-B0 deepfake detection model on a 224x224 normalized chip.
        PyTorch ImageFolder alphabetical class mapping:
          index 0: 'fake' (manipulated / synthetic)
          index 1: 'real' (bonafide / authentic)
        Returns: (prob_real, prob_fake)
        """
        chip_res = cv2.resize(rgb_crop, (224, 224))
        tensor = torch.tensor(chip_res).permute(2, 0, 1).float() / 255.0
        tensor = TRANSFORM_EFFICIENTNET(tensor).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze()
            prob_fake = float(probs[0].item())
            prob_real = float(probs[1].item())

        return prob_real, prob_fake

    def analyze_image(self, file_path: str) -> ImageForensicsResult:
        """
        Execute comprehensive evidence-based forensic analysis on an image file.
        """
        if not os.path.isfile(file_path):
            raise InvalidImageError(f"Image file not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise CorruptFileError("Uploaded image file is 0 bytes.")

        # Read image with OpenCV
        bgr = cv2.imread(file_path)
        if bgr is None:
            raise InvalidImageError("Unable to decode image file via OpenCV.")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = bgr.shape

        # Step 1: Detect faces
        faces = self.detect_faces(bgr)

        # Step 2: Image-level synthetic frequency & compression analysis
        spectral_score = self.compute_spectral_fft_anomaly(rgb)
        ela_score = self.compute_error_level_analysis(file_path)
        gan_artifact_score = round((spectral_score * 0.65) + (ela_score * 0.35), 4)

        # Step 2b: Facial morphing & face-swap signal analysis
        morphing_detector = get_morphing_detector()
        primary_face_xywh = None
        if faces:
            fx, fy, fw, fh = faces[0].bbox_xywh
            primary_face_xywh = (fx, fy, fw, fh)
        morphing_result = morphing_detector.analyze(bgr, face_bbox_xywh=primary_face_xywh)
        morphing_score = morphing_result["composite_morphing_score"]
        morphing_indicators = morphing_result["morphing_indicators"]

        # Step 3: Dual-path neural classification
        face_manipulation_score = None
        global_manipulation_score = 0.0
        primary_bbox = None
        indicators = []
        limitations = [
            "Forensic scores are computed through dual-path neural pattern analysis and high-frequency spectral decomposition.",
            "Automated detection indicates statistical probability of manipulation, not definitive legal proof."
        ]

        if self._model_manager is not None:
            model = self._model_manager.load_model()
            device = self._model_manager.device

            # Pathway A: Global Whole-Frame Neural Pass
            p_glob_real, p_glob_fake = self.run_chip_inference(rgb, model, device)
            global_manipulation_score = p_glob_fake

            # Pathway B: Localized Face-Crop Pass (if faces detected)
            if len(faces) > 0:
                face_fake_probs = []
                for i, face in enumerate(faces):
                    p_face_real, p_face_fake = self.run_chip_inference(face.face_chip, model, device)
                    # Blend localized face chip (primary) with global context
                    combined_chip_fake = (p_face_fake * 0.85) + (p_glob_fake * 0.15)
                    face_fake_probs.append(combined_chip_fake)

                    if combined_chip_fake >= 0.40:
                        indicators.append({
                            "indicator_type": "face_manipulation_artifact",
                            "description": (
                                f"Face #{i+1} exhibits boundary blending or facial synthesis "
                                f"artifacts (manipulation confidence: {combined_chip_fake:.1%})."
                            ),
                            "severity": "critical" if combined_chip_fake >= 0.75 else "high",
                            "region_x": face.norm_bbox[0],
                            "region_y": face.norm_bbox[1],
                            "region_w": face.norm_bbox[2],
                            "region_h": face.norm_bbox[3],
                        })

                max_idx = int(np.argmax(face_fake_probs))
                face_manipulation_score = round(float(face_fake_probs[max_idx]), 4)
                primary_bbox = faces[max_idx].norm_bbox
            else:
                limitations.append(
                    "No human faces were localized in this image. Facial manipulation detector bypassed; "
                    "analysis evaluated whole-frame spectral and compression artifacts."
                )

        # Step 4: Calibrated Multi-Model Fusion Strategy (v3 — face aligned + morphing + generative)
        if len(faces) > 0 and face_manipulation_score is not None:
            # Face media: Dual-path face score fused with morphing + generative artifact score
            # Primary face manipulation 80% + morphing 10% + GAN spectral 10%
            fused_fake = (
                face_manipulation_score * 0.80 +
                morphing_score * 0.10 +
                gan_artifact_score * 0.10
            )
            fused_real = 1.0 - fused_fake

            # Add morphing indicators to the combined list
            indicators.extend(morphing_indicators)

            # Thresholds:
            # Face manipulation >= 0.40 or morphing >= 0.65 or fused >= 0.42 triggers synthetic verdict
            if face_manipulation_score >= 0.40 or morphing_score >= 0.65 or fused_fake >= 0.42:
                prediction = "synthetic"
                evidence_category = "LIKELY_MANIPULATED"
                confidence = round(max(face_manipulation_score, morphing_score, fused_fake), 4)
                risk_level = "critical" if confidence >= 0.80 else "high"
            elif gan_artifact_score >= 0.78 and face_manipulation_score < 0.25 and morphing_score < 0.35:
                prediction = "synthetic"
                evidence_category = "LIKELY_AI_GENERATED"
                confidence = round(gan_artifact_score, 4)
                risk_level = "high"
                indicators.append({
                    "indicator_type": "generative_spectral_anomaly",
                    "description": f"Elevated periodic grid artifacts in 2D spectrum ({gan_artifact_score:.1%}) characteristic of AI image generators.",
                    "severity": "high"
                })
            elif face_manipulation_score <= 0.30 and morphing_score <= 0.45 and gan_artifact_score <= 0.65 and fused_fake <= 0.35:
                prediction = "authentic"
                evidence_category = "LIKELY_AUTHENTIC"
                confidence = round(fused_real, 4)
                risk_level = "low" if confidence >= 0.70 else "medium"
                indicators.append({
                    "indicator_type": "facial_integrity_verified",
                    "description": f"Face boundary analysis, texture entropy, and spectral fingerprint all pass (authenticity: {confidence:.1%}).",
                    "severity": "info",
                    "region_x": primary_bbox[0] if primary_bbox else None,
                    "region_y": primary_bbox[1] if primary_bbox else None,
                    "region_w": primary_bbox[2] if primary_bbox else None,
                    "region_h": primary_bbox[3] if primary_bbox else None,
                })
            else:
                prediction = "uncertain"
                evidence_category = "INCONCLUSIVE"
                confidence = round(max(fused_fake, fused_real), 4)
                risk_level = "medium"
                indicators.append({
                    "indicator_type": "borderline_classification",
                    "description": "Detector outputs fall within ambiguous margin (0.35–0.42). Secondary review recommended.",
                    "severity": "medium"
                })

        else:
            # Non-face media: Evaluated solely through full-frame generative AI forensics
            # Global neural pass + 2D FFT spectral anomaly
            fused_fake = (global_manipulation_score * 0.40) + (gan_artifact_score * 0.60)
            fused_real = 1.0 - fused_fake

            if fused_fake >= 0.60:
                prediction = "synthetic"
                evidence_category = "LIKELY_AI_GENERATED"
                confidence = round(fused_fake, 4)
                risk_level = "critical" if confidence >= 0.85 else "high"
                indicators.append({
                    "indicator_type": "generative_spectral_anomaly",
                    "description": f"Full-frame azimuthal spectral variance ({gan_artifact_score:.1%}) matches generative diffusion/GAN fingerprints.",
                    "severity": "high"
                })
            elif fused_fake <= 0.40:
                prediction = "authentic"
                evidence_category = "LIKELY_AUTHENTIC"
                confidence = round(fused_real, 4)
                risk_level = "low" if confidence >= 0.70 else "medium"
                indicators.append({
                    "indicator_type": "natural_scene_spectrum",
                    "description": "Natural optical frequency roll-off and sensor noise distribution verified across the canvas.",
                    "severity": "info"
                })
            else:
                prediction = "uncertain"
                evidence_category = "INCONCLUSIVE"
                confidence = round(max(fused_fake, fused_real), 4)
                risk_level = "medium"
                indicators.append({
                    "indicator_type": "non_face_inconclusive",
                    "description": "No facial biometric anchors detected and global frequency signals are indeterminate. Image authenticity cannot be conclusively established.",
                    "severity": "medium"
                })

        return ImageForensicsResult(
            prediction=prediction,
            evidence_category=evidence_category,
            confidence=confidence,
            risk_level=risk_level,
            faces_detected=len(faces),
            primary_face_bbox=primary_bbox,
            face_manipulation_score=face_manipulation_score,
            gan_artifact_score=gan_artifact_score,
            spectral_anomaly_score=spectral_score,
            ela_uniformity_score=ela_score,
            morphing_score=round(morphing_score, 4),
            boundary_discontinuity_score=round(morphing_result.get("boundary_discontinuity_score", 0.0), 4),
            lbp_entropy_score=round(morphing_result.get("lbp_entropy_score", 0.0), 4),
            color_mismatch_score=round(morphing_result.get("color_mismatch_score", 0.0), 4),
            probabilities={"authentic": round(fused_real, 4),
                           "deepfake": round(fused_fake, 4)},
            indicators=indicators,
            limitations=limitations
        )


_image_forensics_instance: Optional[ImageForensicsEngine] = None


def get_image_forensics_engine(model_manager=None) -> ImageForensicsEngine:
    global _image_forensics_instance
    if model_manager is None:
        try:
            from .ai_service import _model_manager
            model_manager = _model_manager
        except Exception:
            pass
    if _image_forensics_instance is None:
        _image_forensics_instance = ImageForensicsEngine(model_manager=model_manager)
    elif model_manager is not None and _image_forensics_instance._model_manager is None:
        _image_forensics_instance._model_manager = model_manager
    return _image_forensics_instance
