"""
audio_preprocessor.py — Robust audio decoding, normalization, and feature extraction.

Prepares audio files for the AASIST deepfake detection model:
  1. Validates format, readability, and minimum duration.
  2. Decodes multiple audio codecs (WAV, MP3, FLAC, AAC, M4A, OGG).
  3. Converts multi-channel audio to mono.
  4. Resamples cleanly to model's exact target sample rate (16,000 Hz).
  5. Performs RMS energy check and Voice Activity / Silence detection.
  6. Computes forensic spectral characteristics (spectral flatness, spectral roll-off).
  7. Formats into fixed-length 64,600 sample (~4.04s) windows for AASIST inference.
"""

import os
import io
import math
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
from scipy import signal
from scipy.io import wavfile
import soundfile as sf
from pydub import AudioSegment

from .exceptions import InvalidImageError, CorruptFileError, UnsupportedFormatError

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
TARGET_SAMPLES = 64600  # AASIST input window (~4.0375s at 16kHz)
MIN_DURATION_SECONDS = 0.25
MAX_DURATION_SECONDS = 600.0  # 10 minutes max


@dataclass
class PreprocessedAudio:
    waveform_windows: np.ndarray  # Shape: (N, 64600) float32
    original_sample_rate: int
    duration_seconds: float
    channels: int
    is_silent: bool
    rms_energy: float
    spectral_flatness: float
    spectral_rolloff_hz: float


def load_audio_file(file_path: str) -> Tuple[np.ndarray, int, int]:
    """
    Safely load an audio file into a float32 numpy array and original sample rate.
    Uses soundfile first, falling back to pydub/scipy.
    Returns: (samples, sample_rate, channels)
    """
    if not os.path.isfile(file_path):
        raise InvalidImageError(f"Audio file not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise CorruptFileError("Audio file is empty (0 bytes).")

    # Strategy 1: soundfile (fast C-library for WAV, FLAC, OGG)
    try:
        data, sr = sf.read(file_path, dtype="float32", always_2d=True)
        if len(data) > 0:
            channels = data.shape[1]
            return data, sr, channels
    except Exception as sf_err:
        logger.debug(f"soundfile failed on {file_path}: {sf_err}, trying pydub fallback")

    # Strategy 2: pydub (handles MP3, M4A, AAC, etc.)
    try:
        audio = AudioSegment.from_file(file_path)
        sr = audio.frame_rate
        channels = audio.channels
        samples = np.array(audio.get_array_of_samples())
        if channels > 1:
            samples = samples.reshape((-1, channels))
        else:
            samples = samples.reshape((-1, 1))

        # Normalize int samples to [-1.0, 1.0] float32
        max_val = float(1 << (8 * audio.sample_width - 1))
        data = samples.astype(np.float32) / max_val
        return data, sr, channels
    except Exception as pydub_err:
        logger.debug(f"pydub failed on {file_path}: {pydub_err}")

    # Strategy 3: scipy.io.wavfile (standard PCM WAV)
    try:
        sr, samples = wavfile.read(file_path)
        if samples.ndim == 1:
            samples = samples.reshape((-1, 1))
        channels = samples.shape[1]
        if np.issubdtype(samples.dtype, np.integer):
            info = np.iinfo(samples.dtype)
            data = samples.astype(np.float32) / max(abs(info.min), info.max)
        else:
            data = samples.astype(np.float32)
        return data, sr, channels
    except Exception as wav_err:
        raise CorruptFileError(f"Failed to decode audio file. Format unreadable or corrupted: {wav_err}")


def resample_waveform(waveform: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resamples a 1D mono waveform from orig_sr to target_sr using polyphase resampling.
    """
    if orig_sr == target_sr:
        return waveform

    gcd = math.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd
    return signal.resample_poly(waveform, up, down).astype(np.float32)


def compute_spectral_characteristics(waveform_16k: np.ndarray) -> Tuple[float, float]:
    """
    Computes spectral flatness and 85% spectral roll-off frequency.
    Synthetic vocoders typically exhibit distinct unnatural spectral flatness
    and atypical high-frequency roll-off characteristics.
    """
    if len(waveform_16k) < 512:
        return 0.0, 0.0

    freqs, psd = signal.welch(waveform_16k, fs=TARGET_SAMPLE_RATE, nperseg=min(1024, len(waveform_16k)))
    psd = psd + 1e-12

    # Spectral flatness: geometric mean / arithmetic mean
    geom_mean = np.exp(np.mean(np.log(psd)))
    arith_mean = np.mean(psd)
    spectral_flatness = float(geom_mean / arith_mean)

    # Spectral roll-off (85% energy frequency)
    cum_energy = np.cumsum(psd)
    total_energy = cum_energy[-1]
    cutoff_idx = np.searchsorted(cum_energy, 0.85 * total_energy)
    rolloff_hz = float(freqs[min(cutoff_idx, len(freqs) - 1)])

    return spectral_flatness, rolloff_hz


def segment_waveform_for_model(
    waveform_16k: np.ndarray, target_samples: int = TARGET_SAMPLES
) -> np.ndarray:
    """
    Formats 16kHz audio into (N, target_samples) windows.
    - If shorter than target_samples, repeats waveform (standard ASVspoof protocol).
    - If longer, extracts up to 5 evenly spaced target_samples windows.
    """
    length = len(waveform_16k)
    if length < target_samples:
        tile_count = int(math.ceil(target_samples / length))
        repeated = np.tile(waveform_16k, tile_count)[:target_samples]
        return np.expand_dims(repeated, axis=0)

    # For longer files, sample up to 5 representative windows
    max_windows = 5
    hop = (length - target_samples) // (max_windows - 1) if length > target_samples and max_windows > 1 else target_samples
    hop = max(hop, 1)

    windows = []
    start = 0
    while start + target_samples <= length and len(windows) < max_windows:
        windows.append(waveform_16k[start : start + target_samples])
        start += hop

    if not windows:
        windows.append(waveform_16k[:target_samples])

    return np.array(windows, dtype=np.float32)


def preprocess_audio(file_path: str) -> PreprocessedAudio:
    """
    Main audio preprocessing entrypoint.
    Returns PreprocessedAudio containing model-ready input windows and metadata.
    """
    data, orig_sr, channels = load_audio_file(file_path)

    # Downmix stereo/multichannel to mono
    if channels > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data[:, 0]

    num_samples = len(mono)
    duration_sec = num_samples / float(orig_sr)

    if duration_sec < MIN_DURATION_SECONDS:
        raise CorruptFileError(
            f"Audio duration ({duration_sec:.2f}s) is too short. Minimum duration is {MIN_DURATION_SECONDS}s."
        )

    # Resample to standard 16,000 Hz
    waveform_16k = resample_waveform(mono, orig_sr, TARGET_SAMPLE_RATE)

    # Check for silence or near-zero energy
    rms = float(np.sqrt(np.mean(waveform_16k**2) + 1e-12))
    peak = float(np.max(np.abs(waveform_16k)))
    is_silent = rms < 1e-4 or peak < 1e-3

    # Normalize amplitude to [-1.0, 1.0] if not silent
    if not is_silent and peak > 0:
        waveform_16k = waveform_16k / (peak + 1e-8)

    # Forensic spectral analysis
    flatness, rolloff = compute_spectral_characteristics(waveform_16k)

    # Segment into AASIST input windows
    windows = segment_waveform_for_model(waveform_16k, TARGET_SAMPLES)

    return PreprocessedAudio(
        waveform_windows=windows,
        original_sample_rate=orig_sr,
        duration_seconds=round(duration_sec, 2),
        channels=channels,
        is_silent=is_silent,
        rms_energy=round(rms, 6),
        spectral_flatness=round(flatness, 4),
        spectral_rolloff_hz=round(rolloff, 1),
    )
