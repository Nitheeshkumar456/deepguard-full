# DeepGuard AI Multimodal Authenticity Platform

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Backend Setup (FastAPI)](#backend-setup-fastapi)
5. [Web Frontend Setup](#web-frontend-setup)
6. [Android App Setup](#android-app-setup)
7. [AI Service Setup](#ai-service-setup)
8. [Environment Variables](#environment-variables)
9. [API Endpoints](#api-endpoints)
10. [Testing](#testing)
11. [Production Deployment](#production-deployment)
12. [File Storage Options](#file-storage-options)
13. [License](#license)

---

### Architecture Overview

```
+----------------+      +----------------+      +----------------+
|   Web Frontend | <--->|  FastAPI API   |<---->|   PostgreSQL   |
|   (Vite/NGINX) |      |  (backend)     |      |   (db)         |
+----------------+      +----------------+      +----------------+
        ^                        ^                       ^
        |                        |                       |
        |                        |                       |
        v                        v                       v
+----------------+      +----------------+      +----------------+
|   AI Service   |      |   File Store   |      |   Android App |
| (PyTorch/ONNX) |      | (local or S3) |      | (Kotlin)      |
+----------------+      +----------------+      +----------------+
```

- **Web**: Vite + React compiled into static assets, served by Nginx.
- **Backend**: FastAPI (Python) with PostgreSQL, Alembic migrations, JWT auth.
- **AI Service**: Separate FastAPI service exposing inference endpoints, runs PyTorch models.
- **File Storage**: Local volume by default (`/app/uploads`) or configurable S3 bucket.
- **Android**: Kotlin app communicating with the same backend API.

---

### Local Development Setup

1. **Prerequisites**
   - Docker Desktop (or Docker Engine)
   - Node.js 20+ (for local front‑end dev)
   - Python 3.11 (for backend/AI if you run without Docker)
   - Java 17 + Android Studio (for Android development)

2. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd DeepGuard-AI
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with appropriate values (see section below)
   ```

4. **Start the full stack with Docker Compose**
   ```bash
   docker compose up --build
   ```
   This will spin up PostgreSQL, the backend, the AI service, and the web UI.

5. **Access services**
   - Web UI: http://localhost:3000
   - Backend API: http://localhost:8000
   - AI inference: http://localhost:8500

---

### Database Setup

- **Migrations** are managed by Alembic.
- To apply migrations locally (outside Docker):
  ```bash
  cd backend
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  alembic upgrade head
  ```
- Docker Compose automatically runs migrations on startup via the `command` in `docker-compose.yml` (you can add `alembic upgrade head` as an entrypoint if desired).

---

### Backend Setup (FastAPI)

- **Dockerfile** is located at `backend/Dockerfile` and builds a slim Python image.
- The entrypoint runs:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
- Key configuration lives in `backend/app/config.py` (uses Pydantic BaseSettings).
- JWT authentication, CORS, rate‑limiting and structured JSON logging are configured out‑of‑the‑box.

---

### Web Frontend Setup

- Built with Vite + React (TypeScript). Source code resides in `web/src`.
- **Dockerfile** builds the app in a Node builder stage and serves the static assets via Nginx.
- Development mode (without Docker):
  ```bash
  cd web
  npm ci
  npm run dev   # runs on http://localhost:5173
  ```
- The environment variable `VITE_API_BASE_URL` tells the front‑end where the backend lives.

---

### Android App Setup

- Open `android` folder in Android Studio.
- Ensure `local.properties` points to your SDK location.
- The base API URL is defined in `gradle.properties` (`API_BASE_URL`).
- To build a release APK (CI will provide signing credentials):
  ```bash
  ./gradlew assembleRelease
  ```
- **Signing config** template located at `android/app/signingConfig.gradle.kts` – CI should inject keystore path/password via environment variables.

---

### AI Service Setup

- The AI service runs its own FastAPI app (`service.main:app`).
- **Dockerfile** in `ai/` installs required system libs for PyTorch and OpenCV.
- Model files are expected under `/app/models`. Mount a volume with your trained model(s) when deploying.
- Inference endpoint example:
  ```http
  POST /predict
  Content-Type: multipart/form-data
  file: <image/video/audio>
  ```

---

### Environment Variables

All services read from the same `.env.example` (copy to `.env` and edit). Important keys:

- **Database**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
- **JWT**: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **AI**: `MODEL_DIR`, `AI_WORKERS`
- **File Storage**: `UPLOAD_DIR` (local) or S3 credentials (`S3_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, ...)
- **Web**: `VITE_API_BASE_URL`
- **Android**: `API_BASE_URL`

Never commit real secrets; keep `.env` out of version control (already in `.gitignore`).

---

### API Endpoints

#### Auth (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST   | `/register` | Register new user |
| POST   | `/login`    | Obtain JWT tokens |
| POST   | `/refresh`  | Refresh access token |
| POST   | `/logout`   | Revoke refresh token |
| GET    | `/me`       | Get current user info |
| POST   | `/send-otp` | Send OTP for email verification |
| POST   | `/verify-otp`| Verify OTP |
| POST   | `/forgot-password` | Request password reset |
| POST   | `/reset-password`  | Reset password with token |

#### Upload & Analysis (`/api`) 
| Method | Path | Description |
|--------|------|-------------|
| POST   | `/upload/image` | Upload image for analysis |
| POST   | `/upload/video` | Upload video for analysis |
| POST   | `/upload/audio` | Upload audio for analysis |
| GET    | `/history` | List past analyses |
| GET    | `/analysis/{id}` | Get detailed result |
| GET    | `/reports/{id}`  | Download PDF/HTML report |

All protected routes require `Authorization: Bearer <access_token>` header.

---

### Testing

- **Backend**: `cd backend && pytest -v`
- **AI Service**: `cd ai && pytest -v`
- **Web**: `npm run test` (Jest + React Testing Library) – CI runs on push.
- **Android**: `./gradlew test`
- **End‑to‑End**: Use Cypress (in `web/cypress`) or Playwright to run UI flows against the Docker stack.

---

### Production Deployment

1. **Prepare secrets**
   - Create a secure `.env.production` (git‑ignored) with real values.
   - Optionally store secrets in Docker Secrets or a cloud secret manager and reference them in the compose file.
2. **Build images**
   ```bash
   docker compose -f docker-compose.yml build
   ```
3. **Run stack**
   ```bash
   docker compose -f docker-compose.yml up -d
   ```
4. **Reverse proxy (optional)**
   - If you need TLS termination, place an Nginx or Traefik container in front of the stack and configure certificates (Let’s Encrypt).
5. **Monitoring**
   - Logs are JSON‑structured; forward them to a log aggregator (ELK, Loki).
   - Health‑check endpoint: `GET /api/health` returns `{"status":"ok"}`.
6. **Scaling**
   - Increase `backend` workers or add more AI service replicas behind a load balancer.
   - For GPU inference, replace the `ai` Dockerfile base image with an NVIDIA CUDA image and enable the `nvidia` runtime.

---

### File Storage Options

- **Local** (default): Files stored under `/app/uploads` inside the backend container and persisted via a Docker volume (`./backend/uploads`).
- **AWS S3**: Set `S3_BUCKET_NAME` and related AWS credentials in `.env`. The backend will automatically switch to S3 using `boto3`.
- **GCP Cloud Storage**: Similar approach – set `GCS_BUCKET_NAME` and service account JSON path.

---

### License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

*For any further questions or contributions, please open an issue or submit a pull request.*
