import torch
import cv2
import numpy as np
from PIL import Image
from .model import DeepGuardModel

class DeepfakeDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DeepGuardModel(pretrained=False)
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def preprocess_image(self, image_path: str) -> torch.Tensor:
        # Load and resize image using OpenCV/PIL
        img = Image.open(image_path).convert('RGB')
        img = img.resize((224, 224))
        img_arr = np.array(img).astype(np.float32) / 255.0
        # Reorder dimensions and add batch dim (HWC -> CHW -> BCHW)
        tensor = torch.from_numpy(img_arr).permute(2, 0, 1).unsqueeze(0)
        return tensor.to(self.device)

    def predict(self, image_path: str) -> dict:
        tensor = self.preprocess_image(image_path)
        with torch.no_grad():
            outputs = self.model(tensor)
            probabilities = torch.softmax(outputs, dim=1).squeeze().tolist()
        
        # Assume class 0 is authentic, class 1 is deepfake
        is_authentic = probabilities[0] > probabilities[1]
        confidence = probabilities[0] if is_authentic else probabilities[1]

        return {
            "is_authentic": is_authentic,
            "confidence": float(confidence),
            "probabilities": {
                "authentic": float(probabilities[0]),
                "deepfake": float(probabilities[1])
            }
        }
