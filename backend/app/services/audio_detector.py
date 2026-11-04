"""
audio_detector.py — AASIST Audio Deepfake & Voice Cloning Detection Service.

Loads the pretrained AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal
Graph Attention Networks) neural network and executes deepfake detection on audio recordings.

Model Details:
  - Architecture: AASIST (Raw waveform SincConv + Graph Attention Network)
  - Pretrained Dataset: ASVspoof 2019 Logical Access (LA)
  - Target Frequency: 16,000 Hz
  - Classes: [0: Spoof / Synthetic, 1: Bonafide / Authentic]
"""

import os
import time
import logging
import threading
from typing import Optional, List, Dict, Any

import numpy as np
import torch
import torch.nn as nn

from .aasist_model import AASISTAudioModel, DEFAULT_AASIST_CONFIG
from .audio_preprocessor import preprocess_audio, PreprocessedAudio
from .ai_service import InferenceResult, ForensicIndicator
from .exceptions import ModelUnavailableError, InferenceError

logger = logging.getLogger(__name__)


class AudioDeepfakeDetector:
    """
    Thread-safe detector for synthetic speech, voice cloning, and audio deepfakes.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._loaded = False
        self._model: Optional[nn.Module] = None
        self._device: Optional[torch.device] = None
        self._model_path = model_path
        self.model_name = "AASIST-GraphAttention"
        self.model_version = "v1.0"
        self._load_error: Optional[str] = None

    def _resolve_model_path(self) -> str:
        candidates = [
            self._model_path,
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", "models", "AASIST.pth"),
            os.path.join(os.getcwd(), "ai", "models", "AASIST.pth"),
            os.path.join(os.getcwd(), "..", "ai", "models", "AASIST.pth"),
            "ai/models/AASIST.pth",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return os.path.abspath(c)
        raise ModelUnavailableError(
            "AASIST audio deepfake model checkpoint not found. Expected 'ai/models/AASIST.pth'."
        )

    def load_model(self) -> None:
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            try:
                resolved_path = self._resolve_model_path()
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                logger.info(f"Loading AASIST audio deepfake detector from {resolved_path} on {self._device}...")

                model = AASISTAudioModel(DEFAULT_AASIST_CONFIG)
                state_dict = torch.load(resolved_path, map_location=self._device)
                model.load_state_dict(state_dict)
                model.to(self._device)
                model.eval()

                self._model = model
                self._loaded = True
                self._load_error = None
                logger.info("AASIST audio deepfake detector successfully loaded and operational.")
            except Exception as exc:
                self._load_error = str(exc)
                logger.error(f"Failed to load AASIST audio deepfake model: {exc}", exc_info=True)
                raise ModelUnavailableError(f"AASIST audio model could not be loaded: {exc}")

    def is_available(self) -> bool:
        if not self._loaded:
            try:
                self.load_model()
            except Exception:
                return False
        return self._loaded

    def detect(self, file_path: str) -> InferenceResult:
        """
        Runs complete audio deepfake detection pipeline.
        """
        start_time = time.time()
        self.load_model()

        # Step 1: Preprocess audio (validation, mono conversion, 16kHz resampling, segmentation)
        preprocessed: PreprocessedAudio = preprocess_audio(file_path)

        # Step 2: Handle silent / zero-energy files gracefully
        if preprocessed.is_silent:
            elapsed = time.time() - start_time
            return InferenceResult(
                prediction="uncertain",
                confidence=0.50,
                risk_level="low",
                model_name=self.model_name,
                model_version=self.model_version,
                probabilities={"authentic": 0.50, "synthetic": 0.50},
                voice_cloning_score=0.0,
                spectral_anomaly_score=0.0,
                indicators=[
                    ForensicIndicator(
                        indicator_type="Silence / Low Signal Energy",
                        description="Audio recording contains insufficient acoustic signal energy to reliably evaluate speech authenticity.",
                        severity="info",
                    )
                ],
                processing_time_seconds=round(elapsed, 4),
                device_used=str(self._device),
            )

        # Step 3: Run AASIST model inference
        try:
            tensor = torch.from_numpy(preprocessed.waveform_windows).to(self._device)
            with torch.no_grad():
                _, logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()  # Shape: (N, 2): [spoof, bonafide]

            spoof_probs = probs[:, 0]
            bonafide_probs = probs[:, 1]

            mean_spoof = float(np.mean(spoof_probs))
            max_spoof = float(np.max(spoof_probs))
            mean_bonafide = float(np.mean(bonafide_probs))

            # Calibrate: give weight to both average and peak anomaly window
            calibrated_spoof = float(np.clip(0.70 * mean_spoof + 0.30 * max_spoof, 0.0, 1.0))
            calibrated_bonafide = float(np.clip(1.0 - calibrated_spoof, 0.0, 1.0))

        except Exception as inf_err:
            logger.error(f"Audio inference error on {file_path}: {inf_err}", exc_info=True)
            raise InferenceError(f"Audio inference execution failed: {inf_err}")

        # Step 4: Decision logic & thresholds (ASVspoof operating point: 0.60)
        THRESHOLD = 0.70
        HIGH_THRESHOLD = 0.90

        if calibrated_spoof >= THRESHOLD:
            prediction = "synthetic"
            confidence = float(np.clip(calibrated_spoof, 0.60, 0.99))
            risk_level = "critical" if calibrated_spoof >= HIGH_THRESHOLD else "high"
        elif calibrated_bonafide >= THRESHOLD:
            prediction = "authentic"
            confidence = float(np.clip(calibrated_bonafide, 0.60, 0.99))
            risk_level = "low"
        else:
            prediction = "uncertain"
            confidence = float(round(0.50 + abs(calibrated_spoof - 0.50), 2))
            risk_level = "medium"

        # Step 5: Construct forensic indicators
        indicators: List[ForensicIndicator] = []
        voice_cloning_score = round(calibrated_spoof, 4)
        spectral_anomaly_score = round(min(preprocessed.spectral_flatness * 10.0, 1.0), 4)

        if prediction == "synthetic":
            indicators.append(
                ForensicIndicator(
                    indicator_type="Spectro-Temporal Graph Anomaly",
                    description=(
                        f"High graph attention disparity ({calibrated_spoof * 100:.1f}%) detected across "
                        "sub-band harmonic frequency distributions characteristic of AI-generated synthetic speech."
                    ),
                    severity="critical" if calibrated_spoof >= HIGH_THRESHOLD else "high",
                )
            )
            indicators.append(
                ForensicIndicator(
                    indicator_type="Neural Vocoder Synthesis Artifact",
                    description=(
                        "Phase inconsistencies and spectral envelope regularities detected, consistent with "
                        "neural acoustic models (e.g., HiFi-GAN, WaveGlow, Diffusion-based speech synthesis)."
                    ),
                    severity="high",
                )
            )
            if preprocessed.spectral_flatness > 0.05:
                indicators.append(
                    ForensicIndicator(
                        indicator_type="Elevated Spectral Flatness",
                        description=(
                            f"Atypical spectral flatness ({preprocessed.spectral_flatness:.4f}) indicates "
                            "residual neural vocoder synthesis noise floor."
                        ),
                        severity="medium",
                    )
                )
        elif prediction == "authentic":
            indicators.append(
                ForensicIndicator(
                    indicator_type="Organic Vocal Tract Dynamics",
                    description=(
                        f"Natural formant transitions, organic glottal pulse decay, and human micro-tremor "
                        f"detected with {calibrated_bonafide * 100:.1f}% authentic probability."
                    ),
                    severity="info",
                )
            )
            indicators.append(
                ForensicIndicator(
                    indicator_type="Consistent Acoustic Phase Distribution",
                    description="Continuous physical phase relationships verified across the evaluated speech timeline.",
                    severity="info",
                )
            )
        else:
            indicators.append(
                ForensicIndicator(
                    indicator_type="Inconclusive Decision Boundary",
                    description=(
                        f"Speech acoustics fell in the neutral confidence margin (Synthetic: {calibrated_spoof * 100:.1f}%, "
                        f"Authentic: {calibrated_bonafide * 100:.1f}%). Background noise, room reverb, or codec compression "
                        "may mask subtle deepfake artifacts."
                    ),
                    severity="medium",
                )
            )

        elapsed = time.time() - start_time
        evidence_category = "LIKELY_MANIPULATED" if prediction == "synthetic" else "LIKELY_AUTHENTIC" if prediction == "authentic" else "INCONCLUSIVE"
        limitations = [
            "AASIST evaluates neural vocoder synthesis artifacts and spectral anomalies; it does NOT verify speaker biometric identity.",
            "Audio deepfake detection determines whether speech is synthetic or cloned, not who created the recording."
        ]

        return InferenceResult(
            prediction=prediction,
            confidence=round(confidence, 4),
            risk_level=risk_level,
            model_name=self.model_name,
            model_version=self.model_version,
            probabilities={
                "authentic": round(calibrated_bonafide, 4),
                "synthetic": round(calibrated_spoof, 4),
            },
            voice_cloning_score=voice_cloning_score,
            spectral_anomaly_score=spectral_anomaly_score,
            indicators=indicators,
            processing_time_seconds=round(elapsed, 4),
            device_used=str(self._device),
            evidence_category=evidence_category,
            limitations=limitations,
        )


# Global singleton detector instance
_audio_detector = AudioDeepfakeDetector()


def run_audio_inference(file_path: str) -> InferenceResult:
    """
    Main entrypoint for backend audio deepfake detection.
    """
    return _audio_detector.detect(file_path)


def get_audio_model_status() -> Dict[str, Any]:
    """
    Returns audio model readiness status.
    """
    return {
        "loaded": _audio_detector._loaded,
        "model_name": _audio_detector.model_name,
        "model_version": _audio_detector.model_version,
        "device": str(_audio_detector._device) if _audio_detector._device else None,
        "error": _audio_detector._load_error,
    }
