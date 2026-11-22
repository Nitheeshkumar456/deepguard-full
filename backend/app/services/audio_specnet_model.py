"""
audio_specnet_model.py — DeepGuard Audio Spectrogram Neural Network (SpecNet-v2).

Mirrors ai/src/audio_specnet_model.py for standalone backend inference.
"""

from typing import Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa


def extract_dynamic_spectrogram(
    waveform: np.ndarray,
    sr: int = 16000,
    n_mels: int = 80,
    n_fft: int = 1024,
    hop_length: int = 512,
    target_length: int = 128,
) -> np.ndarray:
    """
    Extracts a 3-channel dynamic spectrogram: [Log-Mel, Delta, Delta-Delta].
    Shape returned: (3, n_mels, target_length), float32.
    """
    if waveform.ndim > 1:
        waveform = np.mean(waveform, axis=1)

    expected_samples = (target_length - 1) * hop_length
    if len(waveform) < expected_samples:
        waveform = np.pad(waveform, (0, expected_samples - len(waveform)), mode="constant")
    elif len(waveform) > expected_samples:
        waveform = waveform[:expected_samples]

    mel = librosa.feature.melspectrogram(
        y=waveform.astype(np.float32),
        sr=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
        fmin=20,
        fmax=8000,
        power=2.0,
    )
    log_mel = np.log10(mel + 1e-6)

    mean = np.mean(log_mel)
    std = np.std(log_mel) + 1e-8
    norm_log_mel = (log_mel - mean) / std

    delta = librosa.feature.delta(norm_log_mel)
    delta2 = librosa.feature.delta(norm_log_mel, order=2)

    spec3 = np.stack([norm_log_mel, delta, delta2], axis=0).astype(np.float32)

    if spec3.shape[2] > target_length:
        spec3 = spec3[:, :, :target_length]
    elif spec3.shape[2] < target_length:
        pad_width = target_length - spec3.shape[2]
        spec3 = np.pad(spec3, ((0, 0), (0, 0), (0, pad_width)), mode="constant")

    return spec3


class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        self.fc1 = nn.Linear(channels, channels // reduction, bias=False)
        self.fc2 = nn.Linear(channels // reduction, channels, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        w = F.adaptive_avg_pool2d(x, (1, 1)).view(b, c)
        w = F.silu(self.fc1(w))
        w = torch.sigmoid(self.fc2(w)).view(b, c, 1, 1)
        return x * w


class AudioResBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, downsample: bool = False):
        super().__init__()
        stride = 2 if downsample else 1
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.se = SEBlock(out_channels)

        if downsample or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.shortcut(x)
        out = F.silu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.se(out)
        out = F.silu(out + res)
        return out


class DeepGuardAudioSpecNet(nn.Module):
    def __init__(self, num_classes: int = 2, in_channels: int = 3):
        super().__init__()
        self.model_name = "DeepGuard-AudioSpecNet-v2"
        self.model_version = "2.0.0"

        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.SiLU(),
        )

        self.stage1 = nn.Sequential(
            AudioResBlock(32, 64, downsample=True),
            AudioResBlock(64, 64, downsample=False),
        )
        self.stage2 = nn.Sequential(
            AudioResBlock(64, 128, downsample=True),
            AudioResBlock(128, 128, downsample=False),
        )
        self.stage3 = nn.Sequential(
            AudioResBlock(128, 256, downsample=True),
            AudioResBlock(256, 256, downsample=False),
        )

        self.avg_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.max_pool = nn.AdaptiveMaxPool2d((1, 1))

        self.classifier = nn.Sequential(
            nn.Dropout(0.30),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.SiLU(),
            nn.Dropout(0.20),
            nn.Linear(128, num_classes),
        )

        self.temperature = nn.Parameter(torch.ones(1) * 1.0)

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.stem(x)
        feat = self.stage1(feat)
        feat = self.stage2(feat)
        feat = self.stage3(feat)
        avg_f = self.avg_pool(feat).flatten(1)
        max_f = self.max_pool(feat).flatten(1)
        embedding = torch.cat([avg_f, max_f], dim=1)
        return embedding

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        embedding = self.extract_features(x)
        logits = self.classifier(embedding)
        return embedding, logits

    def get_calibrated_probabilities(self, x: torch.Tensor) -> torch.Tensor:
        _, logits = self.forward(x)
        temp = torch.clamp(self.temperature, min=0.1, max=10.0)
        calibrated_logits = logits / temp
        probs = F.softmax(calibrated_logits, dim=-1)
        return probs

