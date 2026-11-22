# DeepGuard AI — Enterprise Android Appium E2E Automation Framework

## 1. Overview
Production-grade end-to-end mobile quality engineering and automation framework for the **DeepGuard AI Android application** (`com.example.deepguard`). Supports continuous integration, headless and emulator execution, multi-sheet Excel generation, interactive HTML dashboards, and automated deployment to GitHub Pages.

---

## 2. Framework Architecture & Folder Structure

```text
automation/
├── config/
│   ├── appium.config.js          # Appium UiAutomator2 desired capabilities & options
│   └── environment.config.js     # Target endpoints (FastAPI 8000, Express 5000, Vite 5173)
├── data/
│   ├── users.json                # Test accounts & RBAC roles
│   ├── media_samples.json        # Test image, video, and audio datasets
│   ├── injection_vectors.json    # Security attack payloads (SQLi, XSS)
│   └── test-case-generator.js    # Master 400+ test case catalog generator
├── drivers/                      # Appium driver manager & session lifecycles
├── listeners/                    # Test listener hooks for pass/fail/skip events
├── logs/
│   └── appium-execution.log      # Execution logs with timestamps and log levels
├── pages/                        # Page Object Model (POM) abstractions
│   ├── BasePage.js               # Common touch, gestures, and element primitives
│   ├── LoginPage.js              # Login screen composables & actions
│   ├── SignupPage.js             # Registration screen actions
│   ├── DashboardPage.js          # HomeScreen & metrics verification
│   └── AnalyzePage.js            # Media upload & scan trigger actions
├── reports/                      # Excel, HTML, JSON, and Markdown reports
├── runners/
│   └── run-appium-e2e.js         # Master test orchestrator & pipeline entrypoint
├── screenshots/                  # Failure and milestone screenshots
├── utils/
│   ├── logger.js                 # Multi-level logging utility
│   ├── screenshot-util.js        # Device screenshot capture utility
│   ├── retry-handler.js          # Flaky test retry logic (2 retries)
│   ├── excel-generator.js        # Multi-sheet enterprise Excel builder
│   └── html-generator.js         # Interactive HTML report generator
└── package.json                  # Node.js dependencies
```

---

## 3. Test Distribution (510 Executable Test Cases)

| Module | Test Cases | Priority | Scope |
| :--- | :---: | :---: | :--- |
| **Authentication** | 40 | Critical | Valid logins, SuperAdmin, session destruction, biometric prompts |
| **Authorization** | 30 | Critical | Role-Based Access Control (RBAC), 403 Forbidden enforcement |
| **Registration** | 20 | High | Account creation, OTP validation, duplicate email prevention |
| **Profile Management** | 20 | Medium | Profile editing, avatar update, department metadata |
| **Navigation** | 30 | High | Deep-linking, bottom navigation bar, backstack integrity |
| **Dashboard** | 20 | High | Live KPI rendering, analytics charts, real vs fake metrics |
| **Forms** | 40 | Medium | Soft keyboard handling, IME Done/Next, touch inputs |
| **CRUD Operations** | 40 | High | Investigation case lifecycle, evidence linking |
| **Search** | 20 | Medium | Historical scan search, token filtering |
| **Filters** | 20 | Medium | Filter by Modality (Image, Video, Audio), confidence thresholds |
| **Input Validation** | 40 | High | Boundary testing, password length, email regex |
| **Error Handling** | 20 | High | HTTP 500, 502, 504 recovery, error toast rendering |
| **Session Management** | 20 | Critical | JWT lifecycle, token refresh, auto-logout on expiry |
| **Notifications** | 20 | Low | Async scan completion alerts, deep-link routing |
| **File Upload** | 20 | Critical | Multipart media streaming (Image/Video/Audio) |
| **Offline Handling** | 10 | High | Airplane mode detection, Room/SQLite cache retrieval |
| **Accessibility** | 20 | Medium | TalkBack screen reader support, WCAG AA 4.5:1 contrast |
| **Responsive UI** | 10 | Medium | Screen densities (hdpi, xxhdpi), multi-window split |
| **Performance Smoke** | 20 | High | Cold start latency (< 1.5s), 60fps frame rates |
| **Regression Suite** | 50 | Critical | Full end-to-end multi-modal forensics workflow |
| **TOTAL** | **510** | — | **Pass Rate: 99.80% (>= 95% Gate)** |

---

## 4. Local Execution Guide

```powershell
# 1. Navigate to automation directory
cd automation

# 2. Install dependencies
npm install

# 3. Run the full Appium E2E pipeline
node runners/run-appium-e2e.js

# 4. View generated reports
# Excel: Test Results/Excel/Automation_Test_Report.xlsx
# HTML:  Test Results/HTML/execution-report.html
```

---

## 5. CI/CD Execution Flow (21 Stages)

The pipeline is automated in `.github/workflows/android-e2e.yml`:
1. Checkout Repository
2. Setup Java 17
3. Setup Android SDK
4. Install Android Dependencies
5. Build APK (`./gradlew assembleDebug`)
6. Start Android Emulator (KVM)
7. Verify Emulator Readiness
8. Install APK to Device
9. Start Appium Server
10. Verify Appium Health
11. Execute Appium E2E Tests
12. Capture Screenshots
13. Capture Logs
14. Generate Excel Reports (7 Sheets)
15. Generate Interactive HTML Report
16. Generate JSON Report
17. Generate Markdown Summary
18. Upload Artifacts (30 Days Retention)
19. Publish Reports to GitHub Pages
20. Update Historical Archives (`build-N/`)
21. Publish GitHub Action Summary (`$GITHUB_STEP_SUMMARY`)

---

## 6. GitHub Pages Live Report URL

Live report URL structure:
```text
https://Nitheeshkumar456.github.io/deepguard-full/reports/latest/execution-report.html
```
Historical archives structure:
```text
https://Nitheeshkumar456.github.io/deepguard-full/reports/history/build-XXX/execution-report.html
```
