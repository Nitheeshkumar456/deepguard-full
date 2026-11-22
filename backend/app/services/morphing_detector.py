"""
morphing_detector.py — Facial Morphing & Face-Swap Detection Module.

Implements signal-level analysis to detect facial morphing, face-swapping,
and AI-generated face synthesis artifacts without requiring additional ML models.

Detection techniques:
  1. Facial boundary gradient discontinuity analysis
     — Detects sharp seams at face/background boundaries typical of face-swaps
  2. Texture frequency uniformity analysis
     — Uniform textures indicate GAN-generated skin (no natural micro-texture variance)
  3. Color histogram split analysis
     — Detects color mismatch between face ROI and surrounding skin tones
  4. Edge coherence scoring
     — Detects blending artifacts at face paste boundaries
  5. Local Binary Pattern (LBP) entropy analysis
     — Measures micro-texture complexity; synthetic skin has low LBP entropy

All scores are evidence-based: derived from actual image signal analysis,
never randomized or fabricated.
"""

import logging
import math
from typing import Optional, Dict, Any, Tuple, List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MorphingDetector:
    """
    Detects facial morphing, face-swap, and AI-face-generation artifacts
    using purely signal-based analysis. No additional model weights required.
    """

    def __init__(self):
        self.name = "MorphingDetector-v2"

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def analyze(
        self,
        bgr_image: np.ndarray,
        face_bbox_xywh: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Run all morphing/face-swap detection analyses.

        Args:
            bgr_image: Full BGR image (OpenCV format).
            face_bbox_xywh: Optional face bounding box (x,y,w,h) in pixel coords.

        Returns:
            dict with scores and indicators.
        """
        h, w = bgr_image.shape[:2]
        results: Dict[str, Any] = {
            "boundary_discontinuity_score": 0.0,
            "texture_uniformity_score": 0.0,
            "color_mismatch_score": 0.0,
            "edge_coherence_score": 0.0,
            "lbp_entropy_score": 0.0,
            "composite_morphing_score": 0.0,
            "morphing_indicators": [],
            "indicators": [],
            "face_analyzed": face_bbox_xywh is not None,
        }

        # ── 1. Texture uniformity (whole image) ───────────────────────────
        texture_score = self._texture_uniformity(bgr_image)
        results["texture_uniformity_score"] = round(texture_score, 4)

        # ── 2. LBP entropy score (whole image or face region) ─────────────
        region = bgr_image
        if face_bbox_xywh is not None:
            x, y, fw, fh = face_bbox_xywh
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w, x + fw), min(h, y + fh)
            if (x2 - x1) > 16 and (y2 - y1) > 16:
                region = bgr_image[y1:y2, x1:x2]
        lbp_score = self._lbp_entropy_score(region)
        results["lbp_entropy_score"] = round(lbp_score, 4)

        # ── 3. Boundary discontinuity (only if face bbox provided) ────────
        boundary_score = 0.0
        color_mismatch_score = 0.0
        edge_coherence_score = 0.0

        if face_bbox_xywh is not None:
            x, y, fw, fh = face_bbox_xywh
            boundary_score = self._boundary_discontinuity(bgr_image, x, y, fw, fh)
            color_mismatch_score = self._color_mismatch(bgr_image, x, y, fw, fh)
            edge_coherence_score = self._edge_coherence(bgr_image, x, y, fw, fh)

        results["boundary_discontinuity_score"] = round(boundary_score, 4)
        results["color_mismatch_score"] = round(color_mismatch_score, 4)
        results["edge_coherence_score"] = round(edge_coherence_score, 4)

        # ── 4. Composite morphing score ───────────────────────────────────
        if face_bbox_xywh is not None:
            # Face-aware composite
            composite = (
                boundary_score * 0.30 +
                texture_score * 0.20 +
                color_mismatch_score * 0.20 +
                edge_coherence_score * 0.15 +
                lbp_score * 0.15
            )
        else:
            # No face: rely on texture + lbp
            composite = texture_score * 0.55 + lbp_score * 0.45

        composite = round(float(np.clip(composite, 0.0, 1.0)), 4)
        results["composite_morphing_score"] = composite

        # ── 5. Generate indicators ────────────────────────────────────────
        indicators: List[Dict[str, Any]] = []

        if boundary_score >= 0.60:
            indicators.append({
                "indicator_type": "face_boundary_discontinuity",
                "description": (
                    f"Sharp gradient discontinuity at face boundary region "
                    f"({boundary_score:.1%}) — consistent with face-swap paste seam."
                ),
                "severity": "critical" if boundary_score >= 0.80 else "high",
            })

        if texture_score >= 0.55:
            indicators.append({
                "indicator_type": "synthetic_texture_uniformity",
                "description": (
                    f"Abnormally uniform skin texture ({texture_score:.1%}) detected. "
                    f"AI-generated faces lack natural micro-texture variance."
                ),
                "severity": "high" if texture_score >= 0.70 else "medium",
            })

        if color_mismatch_score >= 0.55:
            indicators.append({
                "indicator_type": "face_skin_tone_mismatch",
                "description": (
                    f"Color histogram divergence between face ROI and surrounding skin "
                    f"({color_mismatch_score:.1%}) — potential face-swap or morphing artifact."
                ),
                "severity": "high" if color_mismatch_score >= 0.70 else "medium",
            })

        if lbp_score >= 0.55:
            indicators.append({
                "indicator_type": "low_lbp_texture_entropy",
                "description": (
                    f"Reduced Local Binary Pattern entropy ({lbp_score:.1%}) in skin region "
                    f"indicates unnaturally smooth AI-synthesized facial texture."
                ),
                "severity": "medium",
            })

        if edge_coherence_score >= 0.60:
            indicators.append({
                "indicator_type": "face_edge_incoherence",
                "description": (
                    f"Edge map discontinuity at face boundary ({edge_coherence_score:.1%}) "
                    f"suggests blending-based face insertion."
                ),
                "severity": "high" if edge_coherence_score >= 0.75 else "medium",
            })

        results["morphing_indicators"] = indicators
        results["indicators"] = indicators
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Internal analysis methods
    # ─────────────────────────────────────────────────────────────────────────

    def _texture_uniformity(self, bgr: np.ndarray) -> float:
        """
        Measures how unnaturally uniform the image texture is.
        GAN-generated faces have extremely low local variance in skin regions.
        Returns [0,1] where high score = suspiciously uniform texture.
        """
        try:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
            # Compute local variance using a sliding window approach
            # Use Laplacian of Gaussian to measure texture energy
            log_response = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
            patch_size = 16
            h, w = gray.shape
            variances = []
            for y in range(0, h - patch_size, patch_size):
                for x in range(0, w - patch_size, patch_size):
                    patch = log_response[y:y + patch_size, x:x + patch_size]
                    variances.append(float(np.var(patch)))

            if not variances:
                return 0.5

            # Natural images have high variance-of-variance
            # Synthetic images are uniformly "smooth" → low var-of-variance
            var_of_vars = float(np.var(variances))
            mean_var = float(np.mean(variances))

            # Score: low mean variance + low var-of-vars → high uniformity → high score
            # Sigmoid calibrated: real images typically have var_of_vars > 500
            uniformity = 1.0 / (1.0 + math.exp(0.003 * (var_of_vars - 800)))
            return float(np.clip(uniformity, 0.0, 1.0))

        except Exception as e:
            logger.debug("Texture uniformity error: %s", e)
            return 0.0

    def _lbp_entropy_score(self, bgr: np.ndarray) -> float:
        """
        Compute Local Binary Pattern entropy.
        Low entropy = very repetitive/smooth texture = likely synthetic.
        Returns [0,1] where high score = low entropy (suspicious).
        """
        try:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            if gray.shape[0] < 16 or gray.shape[1] < 16:
                return 0.0

            # Simple LBP implementation (uniform, 8-point, radius 1)
            gray = gray.astype(np.float32)
            lbp_codes = np.zeros_like(gray, dtype=np.uint8)

            # 8 neighbors
            offsets = [(-1, -1), (-1, 0), (-1, 1),
                       (0, 1), (1, 1), (1, 0),
                       (1, -1), (0, -1)]
            center = gray[1:-1, 1:-1]
            for bit, (dy, dx) in enumerate(offsets):
                neighbor = gray[1 + dy:gray.shape[0] - 1 + dy,
                                1 + dx:gray.shape[1] - 1 + dx]
                lbp_codes[1:-1, 1:-1] += ((neighbor >= center).astype(np.uint8) << bit)

            # Compute histogram entropy
            hist, _ = np.histogram(lbp_codes.ravel(), bins=256, range=(0, 256))
            hist = hist.astype(np.float32) + 1e-10  # Avoid log(0)
            hist /= hist.sum()
            entropy = float(-np.sum(hist * np.log2(hist)))
            max_entropy = math.log2(256)  # ~8 bits

            # High entropy = diverse patterns = natural
            # Low entropy = repetitive = synthetic
            # Normalize: score = 1 - (entropy / max_entropy)
            normalized_entropy = entropy / max_entropy
            score = 1.0 - normalized_entropy

            # Apply calibration: natural images typically have entropy > 0.85 * max
            # Use sigmoid to make it sensitive in the 0.6-0.9 range
            score = float(1.0 / (1.0 + math.exp(-8.0 * (score - 0.25))))
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.debug("LBP entropy error: %s", e)
            return 0.0

    def _boundary_discontinuity(
        self, bgr: np.ndarray, x: int, y: int, w: int, h: int
    ) -> float:
        """
        Measure gradient magnitude discontinuity at face bounding box boundary.
        Face-swap artifacts show sharp discontinuities at paste edges.
        Returns [0,1] where high = suspicious boundary.
        """
        try:
            img_h, img_w = bgr.shape[:2]
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
            # Sobel gradient
            grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            grad_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)

            boundary_width = 8  # pixels around bbox to analyze

            # Build a mask for the boundary region
            x1, y1 = max(0, x - boundary_width), max(0, y - boundary_width)
            x2, y2 = min(img_w, x + w + boundary_width), min(img_h, y + h + boundary_width)
            outer_mask = np.zeros(gray.shape, dtype=bool)
            outer_mask[y1:y2, x1:x2] = True

            inner_x1, inner_y1 = max(0, x + boundary_width), max(0, y + boundary_width)
            inner_x2, inner_y2 = min(img_w, x + w - boundary_width), min(img_h, y + h - boundary_width)
            inner_mask = np.zeros(gray.shape, dtype=bool)
            if inner_y2 > inner_y1 and inner_x2 > inner_x1:
                inner_mask[inner_y1:inner_y2, inner_x1:inner_x2] = True

            boundary_mask = outer_mask & (~inner_mask)
            if not np.any(boundary_mask):
                return 0.0

            boundary_grads = grad_mag[boundary_mask]
            interior_mask = np.zeros(gray.shape, dtype=bool)
            ix1 = max(0, x + boundary_width * 2)
            iy1 = max(0, y + boundary_width * 2)
            ix2 = min(img_w, x + w - boundary_width * 2)
            iy2 = min(img_h, y + h - boundary_width * 2)
            if ix2 > ix1 and iy2 > iy1:
                interior_mask[iy1:iy2, ix1:ix2] = True

            interior_grads = grad_mag[interior_mask] if np.any(interior_mask) else boundary_grads

            boundary_mean = float(np.mean(boundary_grads))
            interior_mean = float(np.mean(interior_grads)) + 1e-5

            # Ratio of boundary to interior gradient
            ratio = boundary_mean / interior_mean
            # High ratio (>2.5) = sharp boundary seam = suspicious
            score = float(1.0 / (1.0 + math.exp(-1.5 * (ratio - 2.5))))
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.debug("Boundary discontinuity error: %s", e)
            return 0.0

    def _color_mismatch(
        self, bgr: np.ndarray, x: int, y: int, w: int, h: int
    ) -> float:
        """
        Detect color histogram mismatch between face ROI and adjacent skin region.
        Face-swaps often have different color temperature/lighting than original.
        Returns [0,1] where high = suspicious color mismatch.
        """
        try:
            img_h, img_w = bgr.shape[:2]
            # Face ROI
            fx1, fy1 = max(0, x), max(0, y)
            fx2, fy2 = min(img_w, x + w), min(img_h, y + h)
            if (fx2 - fx1) < 16 or (fy2 - fy1) < 16:
                return 0.0

            face_roi = bgr[fy1:fy2, fx1:fx2]

            # Context region: expand by 50% to get the surrounding area
            margin_x = int(w * 0.5)
            margin_y = int(h * 0.5)
            cx1, cy1 = max(0, x - margin_x), max(0, y - margin_y)
            cx2, cy2 = min(img_w, x + w + margin_x), min(img_h, y + h + margin_y)

            # Context mask excludes the face itself
            context = bgr[cy1:cy2, cx1:cx2].copy()
            # Zero out the face region in context
            local_fx1 = fx1 - cx1
            local_fy1 = fy1 - cy1
            local_fx2 = local_fx1 + (fx2 - fx1)
            local_fy2 = local_fy1 + (fy2 - fy1)
            context[max(0, local_fy1):local_fy2, max(0, local_fx1):local_fx2] = 0

            # Compute histograms in YCrCb color space (skin-sensitive)
            face_ycrcb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2YCrCb)
            context_ycrcb = cv2.cvtColor(context, cv2.COLOR_BGR2YCrCb)

            # Compare Cr and Cb channels only (chrominance = skin tone)
            divergences = []
            for ch in [1, 2]:  # Cr, Cb
                face_hist = cv2.calcHist([face_ycrcb], [ch], None, [32], [0, 256])
                context_hist = cv2.calcHist([context_ycrcb], [ch], None, [32], [0, 256])
                cv2.normalize(face_hist, face_hist, alpha=1, beta=0, norm_type=cv2.NORM_L1)
                cv2.normalize(context_hist, context_hist, alpha=1, beta=0, norm_type=cv2.NORM_L1)
                bh_dist = cv2.compareHist(face_hist, context_hist, cv2.HISTCMP_BHATTACHARYYA)
                divergences.append(float(bh_dist))

            avg_divergence = float(np.mean(divergences))
            # Bhattacharyya distance: 0 = identical, 1 = completely different
            # Typical real face within context: < 0.3
            # Suspicious mismatch: > 0.5
            score = float(1.0 / (1.0 + math.exp(-8.0 * (avg_divergence - 0.45))))
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.debug("Color mismatch error: %s", e)
            return 0.0

    def _edge_coherence(
        self, bgr: np.ndarray, x: int, y: int, w: int, h: int
    ) -> float:
        """
        Measure edge coherence at face boundaries.
        Blending artifacts from face insertion cause edge discontinuities.
        Returns [0,1] where high = incoherent edges (suspicious).
        """
        try:
            img_h, img_w = bgr.shape[:2]
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            # Use Canny edge detection
            edges = cv2.Canny(gray, threshold1=30, threshold2=100)

            # Sample edge density inside face vs boundary strip
            boundary = 12
            # Inner face region (no boundary)
            ix1 = min(img_w - 1, x + boundary)
            iy1 = min(img_h - 1, y + boundary)
            ix2 = min(img_w, x + w - boundary)
            iy2 = min(img_h, y + h - boundary)

            if ix2 <= ix1 or iy2 <= iy1:
                return 0.0

            inner_edges = edges[iy1:iy2, ix1:ix2]
            inner_density = float(np.mean(inner_edges > 0))

            # Boundary ring
            boundary_mask = np.zeros(gray.shape, dtype=bool)
            bx1, by1 = max(0, x - boundary), max(0, y - boundary)
            bx2, by2 = min(img_w, x + w + boundary), min(img_h, y + h + boundary)
            boundary_mask[by1:by2, bx1:bx2] = True
            boundary_mask[iy1:iy2, ix1:ix2] = False

            boundary_edges_vals = edges[boundary_mask]
            if len(boundary_edges_vals) == 0:
                return 0.0
            boundary_density = float(np.mean(boundary_edges_vals > 0))

            # In natural faces, edge density at boundary ≈ interior
            # Face-swap artifacts: extreme density spike at paste boundary
            if inner_density < 1e-5:
                ratio = 0.0
            else:
                ratio = boundary_density / (inner_density + 1e-5)

            # Calibrated: ratio > 3 is suspicious (artificial edge accumulation at paste line)
            score = float(1.0 / (1.0 + math.exp(-1.2 * (ratio - 3.0))))
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.debug("Edge coherence error: %s", e)
            return 0.0


# Module-level singleton
_detector_instance: Optional[MorphingDetector] = None


def get_morphing_detector() -> MorphingDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = MorphingDetector()
    return _detector_instance
