import torch
import torch.nn as nn

class DeepGuardModel(nn.Module):
    """
    A boilerplate ResNet-based Deepfake detection model structure.
    """
    def __init__(self, pretrained: bool = True):
        super(DeepGuardModel, self).__init__()
        # Placeholder backbone (e.g. ResNet) and linear classifier outputting logits
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1))
        )
        self.classifier = nn.Linear(64, 2) # [Authentic, Deepfake]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x
