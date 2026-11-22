"""
video_temporal_model.py — DeepGuard Video BiGRU Temporal Consistency Model.

Detects inter-frame flickering, face-swap seam jitter, and temporal inconsistencies
across sequential video keyframe representations.
"""

import os
import logging
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class TemporalSelfAttention(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.proj = nn.Linear(hidden_dim, 64)
        self.query = nn.Linear(64, 1, bias=False)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x: (B, T, hidden_dim)
        score = torch.tanh(self.proj(x))  # (B, T, 64)
        score = self.query(score).squeeze(-1)  # (B, T)
        weights = F.softmax(score, dim=-1).unsqueeze(-1)  # (B, T, 1)
        context = torch.sum(x * weights, dim=1)  # (B, hidden_dim)
        return context, weights.squeeze(-1)


class DeepGuardTemporalModel(nn.Module):
    """
    Bi-directional GRU with Temporal Self-Attention for detecting inter-frame
    flickering, face-swap blending inconsistencies, and temporal jitter.
    """
    def __init__(self, feat_dim: int = 1280, hidden_dim: int = 64):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(feat_dim * 2, 128),
            nn.LayerNorm(128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3)
        )
        self.bigru = nn.GRU(
            input_size=128,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        self.attention = TemporalSelfAttention(hidden_dim * 2)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(32, 2)  # [0: Authentic, 1: Synthetic]
        )

    def forward(self, seq_feats: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # seq_feats: (B, T, feat_dim)
        diffs = torch.zeros_like(seq_feats)
        diffs[:, 1:, :] = seq_feats[:, 1:, :] - seq_feats[:, :-1, :]
        combined = torch.cat([seq_feats, diffs], dim=-1)  # (B, T, 2*D)

        x = self.input_proj(combined)  # (B, T, 128)
        gru_out, _ = self.bigru(x)  # (B, T, 128)
        context, attn_weights = self.attention(gru_out)  # (B, 128), (B, T)
        logits = self.classifier(context)  # (B, 2)
        return logits, attn_weights


def load_temporal_model(device: torch.device) -> Optional[DeepGuardTemporalModel]:
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai", "models", "deepguard_temporal_v5.pth"),
        os.path.join(os.getcwd(), "ai", "models", "deepguard_temporal_v5.pth"),
        os.path.join(os.getcwd(), "..", "ai", "models", "deepguard_temporal_v5.pth"),
        "ai/models/deepguard_temporal_v5.pth",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            try:
                model = DeepGuardTemporalModel(feat_dim=1280, hidden_dim=64)
                ckpt = torch.load(c, map_location=device)
                model.load_state_dict(ckpt["model_state_dict"])
                model.to(device)
                model.eval()
                logger.info(f"Loaded DeepGuardTemporalModel from {c} on {device}")
                return model
            except Exception as e:
                logger.warning(f"Could not load temporal model from {c}: {e}")
    return None

