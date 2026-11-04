# Evaluation Overview

## Dataset source
- FaceForensics++ (C23 subset) – a benchmark dataset containing manipulated videos and corresponding real videos.

## Number of samples
- Real samples: *see `real/` directory* (number of files counted at evaluation time).
- Fake samples: *see `fake/` directory* (number of files counted at evaluation time).

## Model
- EfficientNet‑B0 fine‑tuned on FaceForensics++ C23 (binary classifier, class 0 = Real, class 1 = Fake).

## Preprocessing
- EXIF orientation correction, RGB conversion, bicubic resize to 224×224, conversion to float tensor, ImageNet normalization (mean = [0.485, 0.456, 0.406], std = [0.229, 0.224, 0.225]).

## Metrics
- Accuracy, Precision, Recall, F1‑score, Confusion Matrix (TP, TN, FP, FN).
- ROC‑AUC is reported only when both classes are present in the evaluation set.

## Hardware
- Inference runs on the device detected at runtime (`cpu` or `cuda` if a GPU is available).  Performance statistics (average, min, max inference time) are saved in `performance.json`.

## Evaluation date
- 2026‑08‑28 (UTC+05:30).

## Known limitations
- The model is trained and evaluated only on the FaceForensics++ C23 benchmark.  Its performance does **not** generalize automatically to all real‑world AI‑generated content or other deep‑fake generation techniques.
- Accuracy may vary with different video compression levels, lighting conditions, or unseen manipulation methods.
- Hardware differences (GPU vs. CPU) affect inference speed and may influence real‑time applicability.
- The evaluation script processes only the images present in the `real/` and `fake/` folders; no synthetic or duplicated samples are generated.
- Confidence scores are derived from model probabilities and should not be interpreted as absolute certainty.
