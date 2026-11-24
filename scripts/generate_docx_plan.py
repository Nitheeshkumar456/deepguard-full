import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_row(row, is_header=False):
    for cell in row.cells:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        if is_header:
            set_cell_background(cell, "1E3A8A")
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.size = Pt(9.5)

def build_docx(output_path):
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("DeepGuard AI — Multi-Modal Authenticity Platform")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(30, 58, 138) # Navy Blue

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Comprehensive Implementation Plan, Technology Architecture, Dataset Catalog, and Training Report")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(13)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run("System Version: 2.4.0 (Enterprise Edition) | Date: November 2026 | Document Classification: Technical Specification")
    r_meta.font.size = Pt(9)
    r_meta.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Helper for adding Headings
    def add_custom_heading(text, level=1):
        h = doc.add_heading(text, level=level)
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        run = h.runs[0]
        run.font.name = "Arial"
        if level == 1:
            run.font.size = Pt(16)
            run.font.bold = True
            run.font.color.rgb = RGBColor(30, 58, 138)
        elif level == 2:
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = RGBColor(15, 118, 110)
        elif level == 3:
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = RGBColor(51, 65, 85)
        return h

    # Section 1: Executive Summary
    add_custom_heading("1. Executive Summary & Architecture Overview", level=1)
    p = doc.add_paragraph(
        "DeepGuard AI is an enterprise-grade multi-modal synthetic media (deepfake) detection and digital authenticity verification platform. "
        "The system provides real-time forensic auditing and tamper detection across three distinct media modalities: "
        "Still Images (RGB), Full-Motion Video Streams, and Voice/Audio Forensics. "
        "The platform operates on a distributed client-server architecture consisting of a responsive Web Application (React/TypeScript), "
        "an Android Native Client (with barcode/QR deployment and APK distribution), a unified Express API Gateway Proxy (Port 5000), "
        "and a high-performance Python FastAPI Deep Learning Inference Engine (Port 8000)."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)

    # Section 2: Complete Implementation Plan
    add_custom_heading("2. Complete End-to-End Implementation Plan", level=1)
    p = doc.add_paragraph(
        "The platform was engineered following a phased software engineering and machine learning lifecycle. "
        "The table below outlines each phase, milestone, objective, and deliverable executed throughout the project:"
    )
    
    phases = [
        ("Phase 1: Architecture & Data Ingestion", "Engineered multi-modal ingestion pipelines; downloaded FaceForensics++ (c23/c40), ASVspoof 2021, and Celeb-DF; structured manifests.", "Completed"),
        ("Phase 2: Model Architecture & Pre-training", "Integrated EfficientNet-B0/B4 spatial extractors, YuNet face detector, frequency-domain FFT/DCT filters, and AASIST audio vocoder.", "Completed"),
        ("Phase 3: Fine-Tuning & Multi-Modal Calibration", "Executed transfer learning across 2,264 balanced training samples; calibrated probability scores; resolved original model false-positive spikes.", "Completed"),
        ("Phase 4: Backend API & Gateway Development", "Built FastAPI REST endpoints; added Argon2/JWT bearer auth; deployed Express API gateway on port 5000; implemented WebSocket real-time sync.", "Completed"),
        ("Phase 5: Frontend & Android Client Build", "Developed React 18/TypeScript web dashboard; designed Android mobile UI; enabled dynamic username/email authentication and APK QR scanner.", "Completed"),
        ("Phase 6: Comprehensive Testing & Security DAST", "Engineered 510 Appium E2E test cases, 320 Selenium test cases, 100-user baseline load simulation, SAST secret audit, and DAST security checks.", "Completed"),
        ("Phase 7: CI/CD Pipeline & GitHub Pages", "Constructed 21-stage GitHub Actions workflow; published latest and historical HTML/Excel test reports to GitHub Pages; purged legacy logs.", "Completed")
    ]
    
    t_phase = doc.add_table(rows=1, cols=3)
    t_phase.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_phase.rows[0]
    hdr.cells[0].paragraphs[0].add_run("Project Lifecycle Phase")
    hdr.cells[1].paragraphs[0].add_run("Key Activities & Deliverables")
    hdr.cells[2].paragraphs[0].add_run("Status")
    format_row(hdr, is_header=True)
    
    for name, desc, st in phases:
        row = t_phase.add_row()
        row.cells[0].paragraphs[0].add_run(name).font.bold = True
        row.cells[1].paragraphs[0].add_run(desc)
        r_st = row.cells[2].paragraphs[0].add_run(st)
        r_st.font.bold = True
        r_st.font.color.rgb = RGBColor(16, 185, 129)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F8FAFC")

    # Section 3: Technologies Used by Feature
    add_custom_heading("3. Technology Stack & Framework Matrix (By Feature)", level=1)
    p = doc.add_paragraph("The table below details every technology, programming language, framework, and library mapped to its designated feature:")
    
    tech_matrix = [
        ("Web Frontend Interface", "React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Recharts", "Modern, highly responsive SPA dashboard with dark-mode aesthetic and real-time alerts."),
        ("Mobile Client (Android)", "Android Studio, Java/Kotlin, UiAutomator2, Gradle, APK Build Tools", "Native Android client supporting local WiFi & remote deepfake evaluation and live sync."),
        ("API Gateway Proxy", "Node.js (v20+), Express.js, http-proxy-middleware, cors", "Unified reverse proxy on Port 5000 forwarding client requests and serving APK binaries."),
        ("Backend Web Framework", "Python 3.10+, FastAPI, Uvicorn, Pydantic v2, SlowAPI", "Asynchronous microframework handling REST endpoints, rate limiting, and request validation."),
        ("Database & Persistence", "SQLite 3, SQLAlchemy ORM, Alembic schema migrations", "Relational persistence storing user credentials, audit trails, active sessions, and forensic cases."),
        ("Authentication & Security", "PyJWT (JSON Web Tokens), Passlib (Argon2 / Bcrypt), Python-OTP", "Stateless dual-token authentication (Access/Refresh), salted password hashing, and OTP validation."),
        ("Image Deepfake Detection", "PyTorch, Torchvision, Timm, Albumentations, OpenCV (cv2)", "EfficientNet-B0/B4 spatial convolutional networks trained on face crops with frequency FFT analysis."),
        ("Video Stream Forensics", "OpenCV VideoCapture, SciPy, NumPy, PyTorch, YuNet ONNX", "Keyframe decimation, facial landmark tracking, temporal frame-jitter analysis, and morphing detection."),
        ("Audio Voice Cloning Detector", "Librosa, Torchaudio, AASIST Neural Vocoder, PyTorch, SciPy", "Spectro-temporal audio inspection, LFCC/CQCC feature extraction, and neural voice spoofing detection."),
        ("Real-time Synchronization", "WebSocket (Native WebSockets + Python asyncio ws_manager)", "Bidirectional communication synchronizing live profile updates and forensic alerts across clients."),
        ("Automated E2E Testing", "Selenium WebDriver, Appium Mobile Driver, Node.js Test Runners", "End-to-end automated testing validating 510 Appium cases and 320 Selenium web login cases."),
        ("Load & Stress Testing", "k6 (Grafana), Python Requests, OpenPyXL, Pandas", "Simulation of 100 concurrent virtual users generating ~120 RPS with latency percentile tracking."),
        ("Static & Dynamic Security", "Semgrep (SAST), Gitleaks, Python Secrets Auditing", "Codebase vulnerability scanning, secret leakage prevention, and authorization bypass verification."),
        ("CI/CD & Reporting", "GitHub Actions, GitHub Pages, Peaceiris gh-pages, OpenPyXL", "21-stage continuous integration pipeline uploading 7 Excel workbooks and hosting live HTML dashboards.")
    ]

    t_tech = doc.add_table(rows=1, cols=3)
    t_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_tech.rows[0]
    hdr.cells[0].paragraphs[0].add_run("System Feature")
    hdr.cells[1].paragraphs[0].add_run("Technologies & Libraries Used")
    hdr.cells[2].paragraphs[0].add_run("Functional Role & Purpose")
    format_row(hdr, is_header=True)

    for feat, tech, role in tech_matrix:
        row = t_tech.add_row()
        row.cells[0].paragraphs[0].add_run(feat).font.bold = True
        row.cells[1].paragraphs[0].add_run(tech)
        row.cells[2].paragraphs[0].add_run(role)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F1F5F9")

    # Section 4: Deep Dive into Platform Modules
    add_custom_heading("4. Functional Modules & Architecture", level=1)
    
    modules = [
        ("4.1 Image Authenticity Detection Module", 
         "Analyzes static images for generative AI artifacts, blending seams, and facial manipulation. "
         "Combines spatial feature maps extracted via EfficientNet-B0 with high-frequency spatial rich models (SRM) and discrete cosine transform (DCT) residual analysis. "
         "Generates pixel-level heatmaps highlighting modified boundary zones and computes calibrated manipulation probabilities."),
        
        ("4.2 Video Forensics & Temporal Consistency Module",
         "Processes full-length video media via intelligent keyframe decimation. Detects temporal discontinuities, unnatural blinking rates, "
         "color space jitter, and frame-to-frame boundary flickering. Employs lightweight YuNet face detector to isolate facial regions and tracks temporal consistency "
         "using deepguard_temporal_v5.pth to score morphing and face-swap artifacts across sequential frames."),

        ("4.3 Audio & Voice Cloning Forensics Module",
         "Inspects audio streams for synthetic speech generation, voice cloning, and audio splicing. Utilizes AASIST (Automated Audio Spoofing and Interspeech Testing) "
         "neural vocoder models alongside SpecNet (deepguard_audio_v2.pth). Evaluates linear frequency cepstral coefficients (LFCC) and constant Q-transform spectrograms "
         "to identify synthetic vocoder signatures, phase inconsistencies, and temporal cuts."),

        ("4.4 Cross-Modal Late Fusion & Risk Calibration Module",
         "Synthesizes outputs from image, video, and audio forensic sub-engines into a unified authenticity verdict (Authentic vs Synthetic). "
         "Applies isotonic probability calibration to prevent overconfident false alarms and outputs risk classifications (Low, Medium, High, Critical)."),

        ("4.5 Authentication, RBAC & Device Session Module",
         "Enforces secure token-based user authentication using JWT and Argon2. Supports dual-login via case-insensitive Username or Email, "
         "with automated alphanumeric validation. Maintains active device session telemetry (IP address, user-agent, device hardware) with remote revocation capabilities."),

        ("4.6 Case & Investigation Management Module",
         "Provides digital evidence retention for security researchers and forensic auditors. Users can group suspicious media analyses into formal cases, "
         "annotate findings with forensic notes, attach timeline logs, and generate consolidated audit reports in Excel and Markdown formats.")
    ]

    for title, desc in modules:
        add_custom_heading(title, level=2)
        p = doc.add_paragraph(desc)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(6)

    # Section 5: Datasets Used, Storage Structure & File Locations
    add_custom_heading("5. Datasets Used, Storage Structure & Catalog", level=1)
    p = doc.add_paragraph(
        "To ensure high generalizability and resilience against diverse deepfake creation techniques, DeepGuard AI was trained and benchmarked "
        "on diverse public and proprietary datasets. All datasets are centrally managed in the platform repository under `ai/datasets/`."
    )
    
    dataset_catalog = [
        ("expanded_dataset_2k", "ai/datasets/expanded_dataset_2k", "2,264 Images", "748 Real, 748 Fake (Train), 384 Val, 384 Test", "Core fine-tuning corpus containing diverse CelebA, FF++, and diffusion-generated synthetic faces."),
        ("face_crops", "ai/datasets/face_crops", "868 Images", "434 Real, 434 Fake", "Tight facial crops extracted via YuNet and MTCNN with margin padding for localized artifact inspection."),
        ("train / val / test (v1)", "ai/datasets/train, val, test", "1,100 Images", "770 Train (374 Fake, 396 Real), 165 Val, 165 Test", "Initial baseline evaluation corpus derived from FaceForensics++ c23 compression benchmark."),
        ("video_benchmark", "ai/datasets/video_benchmark", "2,175 Video Frames", "Balanced Real & Deepfake Sequences", "Frame-level video test bank extracted from DeepfakeDetection Challenge and Celeb-DF videos."),
        ("video_test_200", "ai/datasets/video_test_200", "200 Videos/Clips", "100 Authentic, 100 Manipulated", "Standardized 200-sample video benchmark suite used for CI/CD regression validation."),
        ("audio_v2_dataset", "ai/datasets/audio_v2_dataset", "250 Audio Files", "125 Real, 125 Synthetic", "Diverse voice cloning dataset with samples from ElevenLabs, Tortoise-TTS, VITS, and clean ASVspoof 2021 speech."),
        ("audio_test_200", "ai/datasets/audio_test_200", "200 Audio Files", "100 Real, 100 Spoofed/Cloned", "Automated 200-sample acoustic benchmark suite evaluating neural vocoder and splicing detection.")
    ]

    t_data = doc.add_table(rows=1, cols=5)
    t_data.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_data.rows[0]
    hdr.cells[0].paragraphs[0].add_run("Dataset Identifier")
    hdr.cells[1].paragraphs[0].add_run("Storage Path")
    hdr.cells[2].paragraphs[0].add_run("Total Files")
    hdr.cells[3].paragraphs[0].add_run("Split / Distribution")
    hdr.cells[4].paragraphs[0].add_run("Content & Forensics Origin")
    format_row(hdr, is_header=True)

    for did, pth, cnt, spl, src in dataset_catalog:
        row = t_data.add_row()
        row.cells[0].paragraphs[0].add_run(did).font.bold = True
        row.cells[1].paragraphs[0].add_run(pth)
        row.cells[2].paragraphs[0].add_run(cnt)
        row.cells[3].paragraphs[0].add_run(spl)
        row.cells[4].paragraphs[0].add_run(src)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F8FAFC")

    # Section 6: Training Methodology & Hyperparameters
    add_custom_heading("6. Model Training Methodology & Hyperparameters", level=1)
    p = doc.add_paragraph(
        "The model training pipeline utilized transfer learning starting from pre-trained ImageNet weights followed by intermediate training "
        "on FaceForensics++ c23. The training procedure was executed via `ai/training/train_expanded_2k.py` and `ai/training/train.py`."
    )
    
    hyperparams = [
        ("Base Backbone Architecture", "EfficientNet-B0 (Pretrained on ImageNet + FaceForensics++)"),
        ("Input Image Dimensions", "224 x 224 pixels (3 RGB channels, normalized with ImageNet mean & std)"),
        ("Optimizer", "AdamW (Weight Decay = 1e-4)"),
        ("Initial Learning Rate", "1e-4 (0.000100) with Cosine Annealing Learning Rate Scheduler"),
        ("Batch Size", "16 samples per mini-batch"),
        ("Loss Function", "Binary Cross-Entropy with Logits Loss (BCEWithLogitsLoss) + Label Smoothing (0.05)"),
        ("Frozen Layers", "Blocks 0 to 5 frozen (143/213 parameters frozen) during initial transfer learning"),
        ("Unfrozen Layers", "Top classification head and Block 6 unfrozen for domain-specific fine-tuning"),
        ("Data Augmentation", "RandomHorizontalFlip (p=0.5), RandomBrightnessContrast, GaussianBlur, ShiftScaleRotate"),
        ("Early Stopping & Patience", "Patience = 8 epochs monitoring Validation Loss and ROC-AUC"),
        ("Checkpoint Output Path", "ai/models/efficientnet_b0_v4_expanded_2k.pth & efficientnet_b0_v3_multimodal.pth")
    ]

    t_hp = doc.add_table(rows=1, cols=2)
    t_hp.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_hp.rows[0]
    hdr.cells[0].paragraphs[0].add_run("Hyperparameter / Setting")
    hdr.cells[1].paragraphs[0].add_run("Configured Value")
    format_row(hdr, is_header=True)

    for k, v in hyperparams:
        row = t_hp.add_row()
        row.cells[0].paragraphs[0].add_run(k).font.bold = True
        row.cells[1].paragraphs[0].add_run(v)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F8FAFC")

    # Section 7: Accuracy Improvement & Comparison
    add_custom_heading("7. Model Training Results: Original vs Upgraded Performance", level=1)
    p = doc.add_paragraph(
        "Fine-tuning DeepGuard AI on the expanded multi-modal dataset produced dramatic improvements across all diagnostic metrics. "
        "Most notably, False Positive Rate (FPR) dropped from 60.61% to 1.52%, while ROC-AUC surged from 0.4362 to 0.9846."
    )

    perf_comparison = [
        ("Accuracy", "45.45%", "93.18%", "+47.73%", "Significant Improvement"),
        ("Precision", "45.95%", "98.31%", "+52.36%", "High Precision (Negligible False Alarms)"),
        ("Recall (Sensitivity)", "51.52%", "87.88%", "+36.36%", "Accurate Deepfake Capture"),
        ("F1-Score", "0.4857", "0.9280", "+0.4423", "Optimal Harmonic Mean"),
        ("ROC-AUC Score", "0.4362", "0.9846", "+0.5484", "Near-Perfect Class Separation"),
        ("Specificity (TNR)", "39.39%", "98.48%", "+59.09%", "Robust Real Image Recognition"),
        ("False Positive Rate (FPR)", "60.61%", "1.52%", "-59.09%", "Massive False Alarm Reduction"),
        ("False Negative Rate (FNR)", "48.48%", "12.12%", "-36.36%", "Drastic Missed-Deepfake Reduction")
    ]

    t_perf = doc.add_table(rows=1, cols=5)
    t_perf.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_perf.rows[0]
    hdr.cells[0].paragraphs[0].add_run("Evaluation Metric")
    hdr.cells[1].paragraphs[0].add_run("Original Checkpoint")
    hdr.cells[2].paragraphs[0].add_run("Upgraded Checkpoint")
    hdr.cells[3].paragraphs[0].add_run("Delta Improvement")
    hdr.cells[4].paragraphs[0].add_run("Forensic Significance")
    format_row(hdr, is_header=True)

    for m, o, u, d, s in perf_comparison:
        row = t_perf.add_row()
        row.cells[0].paragraphs[0].add_run(m).font.bold = True
        row.cells[1].paragraphs[0].add_run(o)
        row.cells[2].paragraphs[0].add_run(u).font.bold = True
        r_d = row.cells[3].paragraphs[0].add_run(d)
        r_d.font.bold = True
        r_d.font.color.rgb = RGBColor(16, 185, 129)
        row.cells[4].paragraphs[0].add_run(s)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F8FAFC")

    # Section 8: Quality Assurance & Generated Artifacts
    add_custom_heading("8. Verification, Testing Suites & Deliverables Catalog", level=1)
    p = doc.add_paragraph(
        "All test execution results and validation artifacts are automatically generated, uploaded to GitHub Actions, "
        "and published to GitHub Pages. Below is the inventory of downloadable Excel workbooks and reports generated by the platform:"
    )

    artifacts = [
        ("Automation_Test_Report.xlsx", "Test Results/Excel/ & reports/excel/", "7 Sheets (510 Appium Android E2E Test Cases across 20 modules)"),
        ("DeepGuard_All_Test_Suites_Results.xlsx", "reports/excel/", "Comprehensive multi-modal evaluation suite covering Image, Video, Audio, Security, and Parity"),
        ("DeepGuard_Baseline_Load_Test_Results.xlsx", "reports/excel/", "100 Virtual Users 1-Minute continuous baseline load test metrics (120.67 RPS, 248.5ms avg latency)"),
        ("Selenium_Frontend_Login_E2E_Test_Results.xlsx", "reports/excel/", "320 Automated Web UI login and security test cases"),
        ("Appium_Frontend_Login_E2E_Test_Results.xlsx", "reports/excel/", "320 Automated Android client login test cases"),
        ("endpoint-inventory.xlsx", "reports/", "Full API security audit of all 58 REST endpoints with RBAC rules and controller mappings"),
        ("execution-report.html & dashboard.html", "Test Results/HTML/ & GitHub Pages", "Interactive executive web dashboard with pass/fail telemetry and historical trends")
    ]

    t_art = doc.add_table(rows=1, cols=3)
    t_art.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_art.rows[0]
    hdr.cells[0].paragraphs[0].add_run("Workbook / Report Artifact")
    hdr.cells[1].paragraphs[0].add_run("Storage Location")
    hdr.cells[2].paragraphs[0].add_run("Coverage & Contents")
    format_row(hdr, is_header=True)

    for art, loc, cov in artifacts:
        row = t_art.add_row()
        row.cells[0].paragraphs[0].add_run(art).font.bold = True
        row.cells[1].paragraphs[0].add_run(loc)
        row.cells[2].paragraphs[0].add_run(cov)
        format_row(row, is_header=False)
        set_cell_background(row.cells[0], "F8FAFC")

    # Final sign-off
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(24)
    r = p_sign.add_run("DeepGuard AI Technical Quality Assurance & Architecture Board\nConfidential — For Internal Project Documentation & Academic Submission")
    r.font.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(148, 163, 184)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    print(f"Successfully generated DOCX report at: {output_path}")

if __name__ == "__main__":
    out1 = "reports/DeepGuard_AI_Complete_Implementation_Plan_and_Technical_Specification.docx"
    out2 = "DeepGuard_AI_Complete_Implementation_Plan.docx"
    build_docx(out1)
    build_docx(out2)

