# api_validation.py
"""Validate that the backend API inference matches the offline inference.

The script performs the following steps for **one image** (or all images in a
folder):

1. Load the pretrained EfficientNet‑B0 checkpoint directly (same code as
   `evaluate.py`).
2. Pre‑process the image using the **exact** pipeline verified earlier.
3. Run inference locally to obtain the predicted class and the probability for
   the *Fake* class.
4. Send the same image to the backend FastAPI endpoint (the project defines the
   image‑analysis route at ``/api/v1/ai/predict`` – adjust if your deployment uses
   a different path).
5. Compare the backend's prediction and probability with the local results.
6. Print a clear report indicating whether they match.

If the predictions differ, the script raises an error so you can investigate any
mismatch in preprocessing, class mapping, or model loading.

Usage examples:
    python ai/evaluation/api_validation.py                # picks a random image
    python ai/evaluation/api_validation.py path/to/img.jpg
    python ai/evaluation/api_validation.py --folder ai/evaluation/real
"""

import argparse
import json
import sys
from pathlib import Path

import requests
import torch
import numpy as np
from torchvision import models, transforms
from PIL import Image

# ---------------------------------------------------------------------------
# Configuration – adjust if your backend runs on a different host/port
# ---------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000/api/v1/ai/predict"  # default endpoint
CHECKPOINT_PATH = (Path(__file__).parents[2] / "ai" / "models" / "efficientnet_b0_ffpp_c23.pth").resolve()

# ---------------------------------------------------------------------------
# Model loading (identical to evaluate.py)
# ---------------------------------------------------------------------------
def load_model():
    model = models.efficientnet_b0(weights=None)
    num_features = model.classifier[1].in_features
    model.classifier[1] = torch.nn.Linear(num_features, 2)
    state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    return model

model = load_model()

# ---------------------------------------------------------------------------
# Pre‑processing – exactly the verified pipeline
# ---------------------------------------------------------------------------
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
preprocess = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

def load_image(img_path: Path) -> Image.Image:
    img = Image.open(img_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def local_inference(img_path: Path):
    img = load_image(img_path)
    tensor = preprocess(img).unsqueeze(0)  # add batch dim
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.nn.functional.softmax(logits, dim=1).squeeze(0).tolist()
        pred = int(np.argmax(probs))
    return {"prediction": pred, "prob_real": probs[0], "prob_fake": probs[1]}

# ---------------------------------------------------------------------------
# Backend API call
# ---------------------------------------------------------------------------
def api_inference(img_path: Path):
    with open(img_path, "rb") as f:
        files = {"file": (img_path.name, f, "application/octet-stream")}
        resp = requests.post(API_URL, files=files)
        resp.raise_for_status()
        data = resp.json()
    result = {"prediction": data.get("prediction"), "confidence": data.get("confidence")}
    if "probabilities" in data:
        probs = data["probabilities"]
        result["prob_real"] = probs[0]
        result["prob_fake"] = probs[1]
    else:
        if result["prediction"] == 1:
            result["prob_fake"] = result["confidence"]
            result["prob_real"] = 1 - result["confidence"]
        else:
            result["prob_real"] = result["confidence"]
            result["prob_fake"] = 1 - result["confidence"]
    return result

# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------
def compare_results(local_res, api_res, tolerance=1e-4):
    same_pred = local_res["prediction"] == api_res["prediction"]
    prob_diff = abs(local_res["prob_fake"] - api_res["prob_fake"])
    same_prob = prob_diff <= tolerance
    return same_pred and same_prob

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Validate backend AI inference against offline script.")
    parser.add_argument("path", nargs="?", help="Path to an image file or a directory containing images.")
    parser.add_argument("--folder", action="store_true", help="Interpret PATH as a folder and test every image inside it.")
    args = parser.parse_args()

    if args.path:
        target = Path(args.path)
        if not target.exists():
            sys.exit(f"Error: {target} does not exist.")
        if target.is_dir() and args.folder:
            img_paths = sorted([p for p in target.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        else:
            img_paths = [target]
    else:
        # No path supplied – pick a deterministic image from evaluation folders if any
        real_dir = Path(__file__).parent / "real"
        fake_dir = Path(__file__).parent / "fake"
        candidates = sorted([p for p in real_dir.iterdir() if p.is_file()] +
                            [p for p in fake_dir.iterdir() if p.is_file()])
        if not candidates:
            sys.exit("No image supplied and evaluation folders are empty – nothing to test.")
        img_paths = [candidates[0]]

    for img_path in img_paths:
        print(f"\n=== Validating {img_path.name} ===")
        local_res = local_inference(img_path)
        api_res = api_inference(img_path)
        print("Local inference:", json.dumps(local_res, indent=2))
        print("API inference  :", json.dumps(api_res, indent=2))
        if compare_results(local_res, api_res):
            print("[SUCCESS] Predictions match (class and probability).")
        else:
            print("[FAILURE] MISMATCH detected!")
            if local_res["prediction"] != api_res["prediction"]:
                print(f"   * Class differs (local={local_res['prediction']}, api={api_res['prediction']})")
            diff = abs(local_res["prob_fake"] - api_res["prob_fake"])
            print(f"   * Fake-class probability difference: {diff:.6f}")
            sys.exit(1)

if __name__ == "__main__":
    main()
