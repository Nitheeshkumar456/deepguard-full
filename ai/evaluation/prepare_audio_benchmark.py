"""
prepare_audio_benchmark.py — Benchmark dataset generation for DeepGuard AI Audio Detection Module.

Generates 20 Genuine human speech samples and 20 Manipulated audio samples across:
  1. Synthetic Neural Vocoder (TTS / AI Generated)
  2. Voice Cloning (Pitch-shifted phase vocoder dispersion)
  3. Spliced Audio (Cut-and-paste boundaries with spectral flux jumps & energy shifts)
  4. Replay Attack (Loudspeaker high-frequency damping + room reverberation)

Genuine speech is sourced from gold-standard human speech recordings (LibriSpeech)
at 16,000 Hz, mono WAV format.
"""

import os
import math
import numpy as np
from scipy import signal
import soundfile as sf
import librosa

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "audio_benchmark"))
GENUINE_DIR = os.path.join(OUTPUT_DIR, "genuine")
MANIPULATED_DIR = os.path.join(OUTPUT_DIR, "manipulated")

os.makedirs(GENUINE_DIR, exist_ok=True)
os.makedirs(MANIPULATED_DIR, exist_ok=True)

SR = 16000
DURATION = 4.04  # ~64,640 samples (matches AASIST 64,600 window)
N_SAMPLES = int(SR * DURATION)


def get_base_human_speech_pool():
    """Extracts 25 genuine human speech clips from LibriSpeech corpora."""
    clips = []
    
    # Extract from libri1 (male) and libri3 (female)
    for name in ['libri1', 'libri3']:
        p = librosa.util.example(name)
        data, orig_sr = sf.read(p)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        data_16k = librosa.resample(data.astype(np.float32), orig_sr=orig_sr, target_sr=SR)
        seg_len = N_SAMPLES
        hop = int(0.9 * SR)
        for i in range(0, len(data_16k) - seg_len, hop):
            seg = data_16k[i : i + seg_len]
            if np.sqrt(np.mean(seg ** 2)) > 0.02:
                seg = seg / (np.max(np.abs(seg)) + 1e-8) * 0.85
                clips.append(seg.astype(np.float32))

    return clips


def make_synthetic_vocoder_sample(seed: int) -> np.ndarray:
    """Generates synthetic speech with rigid neural vocoder harmonics and elevated noise floor."""
    np.random.seed(seed + 100)
    t = np.linspace(0, DURATION, N_SAMPLES, endpoint=False)
    pitch = 140.0 + (seed % 5) * 20.0
    waveform = np.zeros(N_SAMPLES)
    for h in range(1, 28):
        amp = 1.0 / (h ** 0.8)
        waveform += amp * np.sin(2 * np.pi * h * pitch * t)

    upper_noise = np.random.randn(N_SAMPLES)
    b_hp, a_hp = signal.butter(4, 3500 / (SR / 2), btype='high')
    vocoder_noise = signal.lfilter(b_hp, a_hp, upper_noise) * 0.08

    waveform = waveform + vocoder_noise
    waveform = waveform / (np.max(np.abs(waveform)) + 1e-8) * 0.88
    return waveform.astype(np.float32)


def make_voice_cloning_sample(base_speech: np.ndarray, seed: int) -> np.ndarray:
    """Creates voice cloning / pitch shifted speech with vocoder phase dispersion."""
    n_steps = 4.0 if seed % 2 == 0 else -4.0
    shifted = librosa.effects.pitch_shift(base_speech, sr=SR, n_steps=n_steps)
    shifted = shifted / (np.max(np.abs(shifted)) + 1e-8) * 0.85
    return shifted.astype(np.float32)


def make_spliced_audio_sample(base1: np.ndarray, base2: np.ndarray, seed: int) -> np.ndarray:
    """Creates audio with abrupt cut-and-paste splice boundaries (>18 dB shift & high flux)."""
    cut1 = int(1.4 * SR)
    cut2 = int(2.7 * SR)
    spliced = np.zeros(N_SAMPLES, dtype=np.float32)
    spliced[:cut1] = base1[:cut1]
    # Spliced middle section from different speaker with energy boost and room change
    spliced[cut1:cut2] = base2[cut1:cut2] * 2.8
    spliced[cut2:] = base1[cut2:] * 0.4
    spliced = spliced / (np.max(np.abs(spliced)) + 1e-8) * 0.88
    return spliced


def make_replay_attack_sample(base_speech: np.ndarray, seed: int) -> np.ndarray:
    """Loudspeaker playback re-recording: high frequency roll-off and secondary reflection."""
    b_lp, a_lp = signal.butter(6, 6200 / (SR / 2), btype='low')
    replayed = signal.lfilter(b_lp, a_lp, base_speech)
    delay_samples = int((0.040 + (seed % 4) * 0.010) * SR)
    reflected = np.zeros_like(replayed)
    reflected[delay_samples:] = replayed[:-delay_samples] * 0.65
    replayed = replayed + reflected
    replayed = replayed / (np.max(np.abs(replayed)) + 1e-8) * 0.85
    return replayed.astype(np.float32)


def build_benchmark_dataset():
    print("Extracting base human speech pool from LibriSpeech corpora...")
    speech_pool = get_base_human_speech_pool()
    print(f"Obtained {len(speech_pool)} genuine speech clips.")

    if len(speech_pool) < 20:
        raise RuntimeError(f"Need at least 20 speech clips, got {len(speech_pool)}")

    # 1. Save 20 Genuine human speech samples
    print("Writing 20 Genuine human speech samples...")
    for i in range(20):
        clip = speech_pool[i]
        path = os.path.join(GENUINE_DIR, f"authentic_speech_{i+1:02d}.wav")
        sf.write(path, clip, SR)

    # 2. Save 20 Manipulated speech samples
    print("Writing 20 Manipulated audio samples across 4 forensic categories...")
    # Category 1: 5 Vocoder (TTS)
    for j in range(5):
        s = make_synthetic_vocoder_sample(j)
        sf.write(os.path.join(MANIPULATED_DIR, f"synth_vocoder_{j+1:02d}.wav"), s, SR)

    # Category 2: 5 Cloned / Pitch-shifted
    for j in range(5):
        s = make_voice_cloning_sample(speech_pool[j], j)
        sf.write(os.path.join(MANIPULATED_DIR, f"cloned_voice_{j+6:02d}.wav"), s, SR)

    # Category 3: 5 Spliced
    for j in range(5):
        s = make_spliced_audio_sample(speech_pool[j], speech_pool[(j + 5) % len(speech_pool)], j)
        sf.write(os.path.join(MANIPULATED_DIR, f"spliced_audio_{j+11:02d}.wav"), s, SR)

    # Category 4: 5 Replay Attack
    for j in range(5):
        s = make_replay_attack_sample(speech_pool[j + 10], j)
        sf.write(os.path.join(MANIPULATED_DIR, f"replay_attack_{j+16:02d}.wav"), s, SR)

    print("Successfully built benchmark dataset: 20 Genuine, 20 Manipulated.")


if __name__ == "__main__":
    build_benchmark_dataset()
