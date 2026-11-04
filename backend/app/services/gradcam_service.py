"""
gradcam_service.py — Explainable AI (Grad-CAM) visualization for EfficientNet-B0.

Provides technical Grad-CAM attribution heatmaps for the DeepGuard AI platform:
  1. Hooks into the final convolutional layer of the verified EfficientNet-B0 model (features[-1]).
  2. Computes gradient-weighted class activation maps (Grad-CAM) for model predictions.
  3. Resizes, colormaps (JET colormap: blue=low, yellow/green=medium, red=high), and overlays on media.
  4. Generates single-image heatmaps or bounded 5-frame video keyframe heatmaps with disk caching.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

from .ai_service import _model_manager
from .image_preprocessor import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    MODEL_INPUT_SIZE,
    load_and_validate_image,
)
from .exceptions import AIServiceError

logger = logging.getLogger(__name__)

# Base storage directory for cached heatmaps
HEATMAP_CACHE_DIR = Path(__file__).parents[2] / "uploads" / "heatmaps"
HEATMAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class GradCAM:
    """
    Standard Grad-CAM (Gradient-weighted Class Activation Mapping) implementation
    for PyTorch convolutional neural networks.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None
        self.hooks: List[Any] = []
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.hooks.append(self.target_layer.register_forward_hook(forward_hook))
        self.hooks.append(self.target_layer.register_full_backward_hook(backward_hook))

    def remove_hooks(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks = []

    def generate(self, input_tensor: torch.Tensor, target_class: Optional[int] = None) -> Tuple[np.ndarray, int]:
        """
        Generate normalized 2D activation map (values in [0, 1]).
        """
        self.model.eval()
        self.model.zero_grad()

        with torch.enable_grad():
            tensor = input_tensor.clone().detach().requires_grad_(True)
            logits = self.model(tensor)

            if target_class is None:
                target_class = int(torch.argmax(logits, dim=1).item())

            score = logits[0, target_class]
            score.backward()

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Failed to capture feature activations or gradients during backward pass.")

        # Extract [C, H, W]
        act = self.activations[0]
        grad = self.gradients[0]

        # Global average pooling over gradients to get channel importance weights
        weights = torch.mean(grad, dim=(1, 2))  # shape: [C]

        # Weighted combination of forward activation maps
        cam = torch.zeros(act.shape[1:], dtype=torch.float32, device=act.device)
        for i, w in enumerate(weights):
            cam += w * act[i]

        # Apply ReLU to retain only positive influences on the target class
        cam = torch.relu(cam)
        cam_np = cam.detach().cpu().numpy()

        # Normalize to [0, 1]
        c_min = float(np.min(cam_np))
        c_max = float(np.max(cam_np))
        if c_max - c_min > 1e-8:
            cam_np = (cam_np - c_min) / (c_max - c_min)
        else:
            cam_np = np.zeros_like(cam_np)

        return cam_np, target_class


def _get_target_layer(model: nn.Module) -> nn.Module:
    """Resolve the final convolutional layer of EfficientNet-B0."""
    if hasattr(model, "features"):
        return model.features[-1]
    raise AIServiceError("Target model does not possess a recognizable 'features' attribute for Grad-CAM.")


def _preprocess_pil_for_gradcam(pil_img: Image.Image, device: torch.device) -> torch.Tensor:
    """Preprocess PIL image into a model-ready BCHW tensor matching evaluation transforms."""
    preprocess = transforms.Compose([
        transforms.Resize(MODEL_INPUT_SIZE, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN.tolist(), std=IMAGENET_STD.tolist()),
    ])
    return preprocess(pil_img).unsqueeze(0).to(device)


def generate_image_gradcam(
    image_path: str,
    overlay_out_path: Optional[str] = None,
    heatmap_out_path: Optional[str] = None,
    alpha: float = 0.5,
) -> Dict[str, Any]:
    """
    Generate and save a Grad-CAM heatmap visualization for a single image.
    """
    pil_img = load_and_validate_image(image_path).convert("RGB")
    orig_w, orig_h = pil_img.size
    orig_np = np.array(pil_img)

    model = _model_manager.load_model()
    device = _model_manager.device
    target_layer = _get_target_layer(model)

    gradcam = GradCAM(model, target_layer)
    try:
        input_tensor = _preprocess_pil_for_gradcam(pil_img, device)
        cam_2d, target_class = gradcam.generate(input_tensor)
    finally:
        gradcam.remove_hooks()

    # Resize CAM from (7, 7) to original image resolution (W, H)
    cam_resized = cv2.resize(cam_2d, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
    cam_uint8 = np.uint8(255 * np.clip(cam_resized, 0.0, 1.0))

    # Apply standard JET colormap: blue = low, green/yellow = mid, red = high
    heatmap_bgr = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    # Alpha-blend overlay: (1 - alpha) * original + alpha * heatmap
    overlay_rgb = np.uint8((1.0 - alpha) * orig_np + alpha * heatmap_rgb)

    # Save outputs if paths provided
    if overlay_out_path:
        Path(overlay_out_path).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(overlay_rgb).save(overlay_out_path, format="JPEG", quality=92)

    if heatmap_out_path:
        Path(heatmap_out_path).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(heatmap_rgb).save(heatmap_out_path, format="JPEG", quality=92)

    return {
        "target_class": target_class,
        "class_label": "synthetic" if target_class == 1 else "authentic",
        "cam_mean": float(np.mean(cam_2d)),
        "cam_max": float(np.max(cam_2d)),
        "width": orig_w,
        "height": orig_h,
    }


def generate_video_gradcam_frames(
    video_path: str,
    analysis_id: int,
    num_frames: int = 5,
    alpha: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Extract bounded representative keyframes from video and generate Grad-CAM for each.
    """
    if not os.path.isfile(video_path):
        raise AIServiceError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise AIServiceError(f"Could not open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if fps <= 0.0:
        fps = 25.0

    raw_keyframes: List[Tuple[int, np.ndarray]] = []

    try:
        # 1. Seek-based keyframe collection
        if total_frames > 0:
            target_count = min(num_frames, total_frames)
            indices = np.linspace(0, total_frames - 1, num=target_count, dtype=int)
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, bgr = cap.read()
                if ret and bgr is not None and bgr.size > 0:
                    raw_keyframes.append((int(idx), bgr))

        # 2. Sequential fallback if seeking yielded 0 frames or total_frames <= 0
        if len(raw_keyframes) == 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            seq_bgr = []
            max_scan = 600
            while len(seq_bgr) < max_scan:
                ret, bgr = cap.read()
                if not ret or bgr is None or bgr.size == 0:
                    break
                seq_bgr.append(bgr)

            if seq_bgr:
                target_count = min(num_frames, len(seq_bgr))
                sample_indices = np.linspace(0, len(seq_bgr) - 1, num=target_count, dtype=int)
                raw_keyframes = [(int(i), seq_bgr[i]) for i in sample_indices]
    finally:
        cap.release()

    if not raw_keyframes:
        raise AIServiceError("No decodable frames found in video for Grad-CAM generation.")

    frames_meta = []
    model = _model_manager.load_model()
    device = _model_manager.device
    target_layer = _get_target_layer(model)

    gradcam = GradCAM(model, target_layer)
    try:
        for idx, bgr_frame in raw_keyframes:
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(rgb_frame)
            orig_w, orig_h = pil_frame.size

            input_tensor = _preprocess_pil_for_gradcam(pil_frame, device)
            cam_2d, target_class = gradcam.generate(input_tensor)

            cam_resized = cv2.resize(cam_2d, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
            cam_uint8 = np.uint8(255 * np.clip(cam_resized, 0.0, 1.0))

            heatmap_bgr = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
            heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
            overlay_rgb = np.uint8((1.0 - alpha) * rgb_frame + alpha * heatmap_rgb)

            orig_path = HEATMAP_CACHE_DIR / f"{analysis_id}_frame_{idx}_orig.jpg"
            overlay_path = HEATMAP_CACHE_DIR / f"{analysis_id}_frame_{idx}_gradcam.jpg"

            Image.fromarray(rgb_frame).save(orig_path, format="JPEG", quality=90)
            Image.fromarray(overlay_rgb).save(overlay_path, format="JPEG", quality=90)

            timestamp = float(idx / fps)
            frames_meta.append({
                "frame_index": int(idx),
                "timestamp_seconds": round(timestamp, 2),
                "target_class": target_class,
                "class_label": "synthetic" if target_class == 1 else "authentic",
                "original_path": str(orig_path),
                "heatmap_path": str(overlay_path),
            })
    finally:
        gradcam.remove_hooks()

    return frames_meta
