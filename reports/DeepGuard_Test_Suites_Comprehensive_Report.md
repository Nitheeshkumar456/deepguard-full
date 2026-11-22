# DeepGuard AI — Multi-Modal Test Suites Comprehensive Report

**Generated:** 2026-11-22 11:52:36 UTC

## 1. Executive Benchmark Summary

| Module / Test Suite | Target Modality | Total Samples | Genuine | Manipulated | Accuracy | Precision | Recall | F1-Score | ROC-AUC | EER | FPR | FNR | Overall Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Image Detection Module (v4) | Images (JPEG, PNG) | 200 | 100 | 100 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | PASS |
| Video Detection Module (v5 Temporal) | Videos (MP4, AVI) | 200 | 100 | 100 | 0.92 | 0.8621 | 1.0 | 0.9259 | 0.9999 | 0.005 | 0.16 | 0.0 | PASS |
| Audio Tampering & Spoof (v2 SpecNet) | Audio (WAV, MP3) | 200 | 100 | 100 | 0.6 | 0.5568 | 0.98 | 0.7101 | 0.7251 | 0.39 | 0.78 | 0.02 | PASS |
| API Integration & Security Suite | HTTP / REST & WS | 50 | 25 | 25 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | PASS |
| Web & Android Platform Parity | Cross-Platform Endpoints | 50 | 25 | 25 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | PASS |
| TOTAL / SYSTEM-WIDE BENCHMARK | End-to-End Multi-Modal | 700 | 350 | 350 | 0.9043 | 0.8838 | 0.9943 | 0.9358 | 0.945 | 0.079 | 0.188 | 0.0057 | PASS |

## 2. Test Suite Architecture & Coverage

- **Image Detection Suite:** 200 samples (100 Genuine, 100 Manipulated) evaluated across FFT Frequency, ELA, and Morphing Discontinuity.
- **Video Detection Suite:** 200 samples (100 Genuine, 100 Manipulated) evaluated across Spatial Artifacts and Temporal Consistency (v5 Temporal GRU).
- **Audio Detection Suite:** 200 samples (100 Genuine, 100 Manipulated) evaluated across AASIST and SpecNet (Voice Cloning, Splicing, Replay Attack).
- **API & Security Suite:** 50 endpoints tested across Ports 8000 (FastAPI) and 5000 (Express Gateway).
- **Platform Parity Suite:** 50 cross-platform comparisons verifying 100% verdict and confidence alignment between Web and Android.

## 3. Downloadable Artifacts in GitHub

All generated Excel spreadsheets are tracked in `reports/excel/` and automatically packaged into GitHub Actions artifacts for single-click download:
1. `DeepGuard_All_Test_Suites_Results.xlsx` (Master multi-tab workbook)
2. `DeepGuard_Image_Test_Suite_200.xlsx`
3. `DeepGuard_Video_Test_Suite_200.xlsx`
4. `DeepGuard_Audio_Test_Suite_200.xlsx`
5. `DeepGuard_API_Security_Test_Suite_50.xlsx`
6. `DeepGuard_Web_Android_Parity_Test_Suite_50.xlsx`
