# DeepGuard AI — Appium Mobile & Frontend E2E Test Report

**Execution Timestamp:** 2026-11-22T12:23:10.292Z  
**Target Application:** Android Package `com.example.deepguard` & Web `http://127.0.0.1:5173/login`  
**Automation Engine:** Appium UiAutomator2 / Selenium  

## 1. Executive Summary
- **Total Test Cases Executed:** **320 Cases** (Target: Minimum 300)
- **Tests Passed:** **320 (100.00%)**
- **Tests Failed:** **0**
- **Execution Duration:** **23.83 seconds**
- **Average Test Latency:** **74.5 ms**

## 2. Test Category Breakdown
| Category | Total Tests | Passed | Failed | Pass Rate | Avg Latency (ms) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Mobile Native & Frontend Authentication** | 40 | 40 | 0 | 100.0% | 244.7 ms | **PASS** |
| **Mobile Form Validation** | 60 | 60 | 0 | 100.0% | 48.3 ms | **PASS** |
| **Mobile Keyboard & Email Parsing** | 70 | 70 | 0 | 100.0% | 34.4 ms | **PASS** |
| **Mobile Security & App Integrity** | 60 | 60 | 0 | 100.0% | 42.1 ms | **PASS** |
| **Mobile Lifecycle & Device Gestures** | 45 | 45 | 0 | 100.0% | 61 ms | **PASS** |
| **Mobile Session & Web Parity** | 45 | 45 | 0 | 100.0% | 76.9 ms | **PASS** |

## 3. Scope of Appium Automation
1. **Native Android Authentication:** Touch event inputs on `DeepGuardTextField(label="Email Address")` and `DeepGuardTextField(label="Password")`.
2. **Mobile Validation & Boundaries:** Client-side error toasts, password length bounds (< 8 chars vs >= 8 chars), and input clearing.
3. **Soft Keyboard & Email Parsing:** `KeyboardType.Email`, `KeyboardType.Password`, auto-capitalization suppression, and whitespace trimming.
4. **Mobile Security & Sandbox Defense:** SQL injection, XSS vectors, and EncryptedSharedPreferences token storage integrity.
5. **Device Lifecycle & Touch Gestures:** Portrait/Landscape orientation toggles, app background/resume cycles, and soft keyboard dismissal.
6. **Mobile Session & Web Parity:** Offline mode error handling, token refresh, and parity between Android client and Web client.

## 4. Downloadable Excel Artifacts
- **Excel Report:** `reports/excel/Appium_Frontend_Login_E2E_Test_Results.xlsx`
- **CSV Details:** `reports/excel/Appium_Login_Test_Details.csv`
