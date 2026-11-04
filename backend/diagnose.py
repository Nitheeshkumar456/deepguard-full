"""
diagnose.py — Quick diagnostic to check model weights and calibration.
Run from backend/ folder: python diagnose.py
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))

import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
MODEL_PATH   = os.path.join(PROJECT_ROOT, "ai", "models", "efficientnet_b0_ffpp_c23.pth")
AASIST_PATH  = os.path.join(PROJECT_ROOT, "ai", "models", "AASIST.pth")

print("=" * 60)
print("DeepGuard AI — Model Diagnostics")
print("=" * 60)

# ── 1. Check files ────────────────────────────────────────────
print(f"\n[1] EfficientNet weights: {MODEL_PATH}")
print(f"    Exists: {os.path.isfile(MODEL_PATH)}, Size: {os.path.getsize(MODEL_PATH)//1024} KB" if os.path.isfile(MODEL_PATH) else "    ❌ NOT FOUND")

print(f"\n[2] AASIST weights:       {AASIST_PATH}")
print(f"    Exists: {os.path.isfile(AASIST_PATH)}, Size: {os.path.getsize(AASIST_PATH)//1024} KB" if os.path.isfile(AASIST_PATH) else "    ❌ NOT FOUND")

# ── 2. Load EfficientNet and inspect weights ──────────────────
if os.path.isfile(MODEL_PATH):
    print("\n[3] Loading EfficientNet-B0 weights...")
    try:
        state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        print(f"    Keys: {list(state.keys())[:5]} ...")
        # Sum all weights to see if they're all zeros (untrained)
        total_weight_sum = sum(v.abs().sum().item() for v in state.values())
        total_params = sum(v.numel() for v in state.values())
        mean_weight = total_weight_sum / (total_params + 1e-8)
        print(f"    Total params: {total_params:,}")
        print(f"    Mean |weight|: {mean_weight:.6f}")
        if mean_weight < 0.001:
            print("    ⚠️  WARNING: Weights appear near-zero (untrained/corrupted model!)")
        else:
            print("    ✅ Weights look healthy")
    except Exception as e:
        print(f"    ❌ Failed to load: {e}")

# ── 3. Run a test image inference with a random tensor ────────
print("\n[4] Test inference on a random 224x224 tensor (should give ~50/50 if untrained)...")
try:
    class DeepGuardModel(nn.Module):
        def __init__(self):
            super().__init__()
            base = efficientnet_b0(weights=None)
            self.features  = base.features
            self.avgpool   = base.avgpool
            self.classifier = base.classifier
            self.classifier[1] = nn.Linear(self.classifier[1].in_features, 2)
        def forward(self, x):
            x = self.features(x)
            x = self.avgpool(x)
            x = torch.flatten(x, 1)
            return self.classifier(x)

    model = DeepGuardModel()
    if os.path.isfile(MODEL_PATH):
        state = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
    model.eval()

    import torchvision.transforms as T
    transform = T.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])

    results = []
    for trial in range(5):
        # Simulate a "natural" image: random noise in 0-1 range (like a real photo sensor)
        rand_img = torch.rand(3, 224, 224)
        tensor   = transform(rand_img).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
            probs  = torch.softmax(logits, dim=1).squeeze()
        p_real = float(probs[0])
        p_fake = float(probs[1])
        results.append((p_real, p_fake))
        print(f"    Trial {trial+1}: p_authentic={p_real:.4f}, p_synthetic={p_fake:.4f}  → {'authentic' if p_real > p_fake else 'SYNTHETIC ⚠️'}")

    avg_fake = sum(r[1] for r in results) / len(results)
    print(f"\n    Average synthetic probability: {avg_fake:.4f}")
    if avg_fake > 0.65:
        print("    ❌ DIAGNOSIS: Model is BIASED toward synthetic — classifier head likely miscalibrated or trained on wrong label assignment.")
        print("       Class 0 should = REAL, Class 1 should = FAKE. Check state_dict key ordering.")
    elif avg_fake > 0.45:
        print("    ⚠️  DIAGNOSIS: Model shows mild synthetic bias. May need threshold tuning.")
    else:
        print("    ✅ DIAGNOSIS: Model correctly leans authentic for random noise.")

except Exception as e:
    print(f"    ❌ Failed: {e}")

# ── 4. Check FFT ELA bias ─────────────────────────────────────
print("\n[5] Testing FFT spectral score on a pure random image (should be ~0.50)...")
try:
    import cv2
    gray = np.random.randint(0,255,(256,256),dtype=np.uint8).astype(np.float32)
    dft = np.fft.fft2(gray)
    dft_shift = np.fft.fftshift(dft)
    mag = 20 * np.log(np.abs(dft_shift) + 1e-8)
    cy, cx = 128,128
    y,x = np.ogrid[:256,:256]
    dist = np.sqrt((x-cx)**2 + (y-cy)**2)
    hf_mean = float(np.mean(mag[dist>70]))
    lf_mean = float(np.mean(mag[dist<35]))
    ratio = hf_mean / (lf_mean + 1e-5)
    score = float(1.0/(1.0+math.exp(-12.0*(ratio-0.60))))
    print(f"    Ratio={ratio:.4f}, Spectral FFT score={score:.4f}")
    if score > 0.65:
        print(f"    ⚠️  WARNING: FFT baseline for random noise = {score:.4f} (>0.65). \n       The sigmoid sigmoid center=0.60 is too low — real images will hit 'synthetic' zone.")
    else:
        print(f"    ✅ FFT baseline is fine: {score:.4f}")
except Exception as e:
    print(f"    ❌ Failed: {e}")

print("\n" + "=" * 60)
print("Diagnostics complete.")
print("=" * 60)
