# DeepGuard AI — 100-User 60-Second Baseline & Load Test Report

**Execution Date:** 2026-11-22 12:12:46 UTC

## 1. Key Performance Indicators (KPIs)

- **Concurrent Users:** 100 Virtual Users running in parallel
- **Duration:** 61.03 seconds
- **Total Requests:** 17,989 requests
- **Throughput (RPS):** **294.73 requests/sec**
- **Success Rate:** **100.00%**
- **Data Transferred:** 35529.45 MB (596090.27 KB/s)

### Response Times Breakdown
- **Fastest (Min):** `11.08 ms`
- **Average (Mean):** `312.14 ms`
- **Median (50th percentile):** `185.08 ms`
- **90th Percentile (p90):** `705.84 ms`
- **95th Percentile (p95):** `974.10 ms`
- **Slowest (Max):** `5842.90 ms`

## 2. Endpoint Performance Table

| Endpoint Name | HTTP Method | URL Tested | Total Requests | RPS | Success Rate | Min Latency (ms) | Avg Latency (ms) | p50 Latency (ms) | p95 Latency (ms) | Max Latency (ms) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APK Download Probe | HEAD | http://127.0.0.1:5000/download-apk | 1771 | 29.0 | 1.0 | 23.34 | 140.28 | 96.36 | 311.6 | 3643.88 | PASS |
| Auth Me (Unauth Check) | GET | http://127.0.0.1:8000/api/auth/me | 1817 | 29.8 | 1.0 | 31.2 | 416.28 | 286.96 | 1137.06 | 5387.52 | PASS |
| Express Gateway Health | GET | http://127.0.0.1:5000/express/health | 4515 | 74.0 | 1.0 | 11.08 | 143.76 | 93.37 | 324.31 | 4680.91 | PASS |
| FastAPI Core Probe | GET | http://127.0.0.1:8000/ | 4506 | 73.8 | 1.0 | 30.08 | 393.77 | 274.24 | 1092.1 | 5842.9 | PASS |
| OpenAPI JSON Schema | GET | http://127.0.0.1:8000/openapi.json | 2714 | 44.5 | 1.0 | 32.45 | 401.97 | 297.09 | 1087.2 | 5715.57 | PASS |
| Swagger OpenAPI Docs | GET | http://127.0.0.1:8000/docs | 2666 | 43.7 | 1.0 | 28.27 | 411.05 | 288.05 | 1109.88 | 5434.85 | PASS |

## 3. Second-by-Second Timeline (Summary Sample)

| Second | Active Users | Requests Completed | Current RPS | Min Latency (ms) | Avg Latency (ms) | Max Latency (ms) | Errors | System State |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 100 | 199 | 199 | 11.08 | 1075.69 | 5842.9 | 0 | STABLE |
| 2 | 100 | 62 | 62 | 192.4 | 2113.89 | 5123.46 | 0 | STABLE |
| 3 | 100 | 28 | 28 | 452.01 | 2045.91 | 3718.69 | 0 | STABLE |
| 4 | 100 | 36 | 36 | 517.45 | 1646.27 | 2807.67 | 0 | STABLE |
| 5 | 100 | 33 | 33 | 369.86 | 1119.94 | 1782.96 | 0 | STABLE |
| 6 | 100 | 228 | 228 | 27.25 | 225.07 | 1754.45 | 0 | STABLE |
| 7 | 100 | 381 | 381 | 25.71 | 255.07 | 1222.87 | 0 | STABLE |
| 8 | 100 | 329 | 329 | 30.15 | 287.99 | 2530.97 | 0 | STABLE |
| 9 | 100 | 355 | 355 | 27.39 | 253.28 | 1334.7 | 0 | STABLE |
| 10 | 100 | 355 | 355 | 29.64 | 264.28 | 2104.42 | 0 | STABLE |
| 11 | 100 | 358 | 358 | 29.09 | 253.12 | 1835.35 | 0 | STABLE |
| 12 | 100 | 329 | 329 | 22.55 | 312.91 | 2092.14 | 0 | STABLE |
| 13 | 100 | 231 | 231 | 36.3 | 404.33 | 2824.35 | 0 | STABLE |
| 14 | 100 | 281 | 281 | 36.85 | 316.91 | 2519.24 | 0 | STABLE |
| 15 | 100 | 272 | 272 | 34.17 | 351.47 | 1971.0 | 0 | STABLE |

*(Full 60-second second-by-second timeline available in the Excel report)*

## 4. Downloadable Excel Artifacts

All results are saved in `reports/excel/DeepGuard_Baseline_Load_Test_Results.xlsx` and uploaded to GitHub Actions artifacts.
