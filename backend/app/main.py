from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
import logging
import re

from .config import settings
from .database import engine, Base
from .routes.auth import router as auth_router
from .routes.analysis import router as analysis_router, system_router
from .routes.settings import router as settings_router
from .routes.sync import router as sync_router
from .routes.cases import router as cases_router
from .routes.compare import router as compare_router
from .routes.sessions import router as sessions_router
from .routes.data_export import router as data_export_router
from .models import auth as auth_models
from .models import analysis as analysis_models
from .models import settings as settings_models
from .models import investigation as investigation_models
from .models import security as security_models
from .services.websocket_manager import ws_manager
import asyncio

# Initialize rate limiter
# Limiter initialized in backend/app/limiter.py

# Logging filter to redact tokens and passwords
class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Redact JWT tokens
            record.msg = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer <redacted>", record.msg)
            # Redact passwords in logs
            record.msg = re.sub(r"password=[^\s&]+", "password=<redacted>", record.msg)
        return True

# Apply filter to root logger
logging.getLogger().addFilter(RedactFilter())

# Global exception handler for internal server errors
async def unicorn_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multimodal Authenticity Platform API for deepfake detection",
    version="2.0.0",
)

# Attach slowapi rate limiter to application state
app.state.limiter = limiter
# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Add generic internal server error handler
app.add_exception_handler(Exception, unicorn_exception_handler)

# Configure CORS based on environment
cors_origins = ["*"] if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(compare_router)
app.include_router(analysis_router)
app.include_router(system_router)
app.include_router(settings_router)
app.include_router(sync_router)
app.include_router(cases_router)
app.include_router(sessions_router)
app.include_router(data_export_router)

from pydantic import BaseModel
from sqlalchemy.sql import text

class HealthResponse(BaseModel):
    status: str

class StatusResponse(BaseModel):
    status: str
    version: str

@app.on_event("startup")
async def startup_db_check():
    """
    On server startup, verify that the database engine can establish connection,
    ensure all database tables are created, check column migrations,
    and attach the running asyncio event loop to WebSocketConnectionManager.
    """
    # Attach running event loop to ws_manager
    ws_manager.set_loop(asyncio.get_running_loop())

    try:
        # Ensure all tables exist
        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

            # Check and safely add version and updated_at columns to users table if SQLite
            try:
                res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                col_names = [r[1] for r in res]
                if "version" not in col_names:
                    conn.execute(text("ALTER TABLE users ADD COLUMN version INTEGER DEFAULT 1"))
                if "updated_at" not in col_names:
                    conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))

                # Check and safely add device tracking columns to sessions table if SQLite
                s_res = conn.execute(text("PRAGMA table_info(sessions)")).fetchall()
                s_cols = [r[1] for r in s_res]
                if "device_name" not in s_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN device_name VARCHAR(128)"))
                if "platform" not in s_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN platform VARCHAR(64)"))
                if "ip_address" not in s_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN ip_address VARCHAR(64)"))
                if "user_agent" not in s_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN user_agent VARCHAR(256)"))
                if "last_active_at" not in s_cols:
                    conn.execute(text("ALTER TABLE sessions ADD COLUMN last_active_at DATETIME"))

                # v2 — morphing/face-swap score columns on analysis_results
                ar_res = conn.execute(text("PRAGMA table_info(analysis_results)")).fetchall()
                ar_cols = [r[1] for r in ar_res]
                for col in ("morphing_score", "boundary_discontinuity_score",
                            "lbp_entropy_score", "color_mismatch_score"):
                    if col not in ar_cols:
                        conn.execute(text(f"ALTER TABLE analysis_results ADD COLUMN {col} FLOAT"))

                conn.commit()
            except Exception as schema_exc:
                logging.debug(f"Schema upgrade check note: {schema_exc}")

        # Pre-warm AI service status cache so incoming requests are instant
        try:
            from .services.ai_service import get_model_status
            get_model_status()
        except Exception as warmup_err:
            logging.debug(f"AI service warmup note: {warmup_err}")

        print("Database connection check and table initializations successful.")
    except Exception as e:
        print(f"WARNING: Database connection failed: {e}")

@app.get("/", summary="Root Health Check")
@app.get("/health", response_model=HealthResponse, summary="Direct Liveness Check")
@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    """
    Verify basic service liveness state.
    """
    return {"status": "ok"}

@app.get("/api/v1/status", response_model=StatusResponse)
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/api/v1/ai/status", summary="AI Model Status")
async def get_ai_status():
    """
    Return the current status of the AI inference model:
    loaded, model name, version, device, and whether trained weights are in use.
    """
    from .services.ai_service import get_model_status
    return get_model_status()

@app.post("/detect-image", summary="Direct AI Image Prediction")
@app.post("/api/v1/ai/detect-image", summary="Direct AI Image Prediction")
@app.post("/api/v1/ai/predict-image", summary="Direct AI Image Prediction")
@app.post("/api/v1/ai/predict", summary="Direct AI Image Prediction")
async def predict_image(file: UploadFile = File(...)):
    """
    Direct AI prediction endpoint for image authenticity evaluation.
    Class 0 = Real, Class 1 = Fake.
    """
    import tempfile, os
    from fastapi import HTTPException
    from .services.ai_service import run_image_inference
    from .services.exceptions import AIServiceError

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file provided.")

    suffix = os.path.splitext(file.filename or "")[1] or ".jpg"
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="deepguard_predict_")
    os.close(fd)

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        result = run_image_inference(temp_path)
        prob_real = result.probabilities.get("authentic", 1.0 - (result.face_manipulation_score or 0.0))
        prob_fake = result.probabilities.get("deepfake", result.face_manipulation_score or 0.0)
        pred_class = 1 if (result.prediction == "synthetic" or prob_fake >= 0.40) else 0
        
        return {
            "prediction": pred_class,
            "label": "Real" if pred_class == 0 else "Fake",
            "confidence": result.confidence,
            "probabilities": [prob_real, prob_fake],
            "real_probability": prob_real,
            "fake_probability": prob_fake,
            "inference_time_ms": round(result.processing_time_seconds * 1000, 2),
        }
    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.post("/detect-video", summary="Direct AI Video Detection")
@app.post("/api/v1/ai/detect-video", summary="Direct AI Video Detection")
@app.post("/api/v1/ai/predict-video", summary="Direct AI Video Detection")
async def detect_video(file: UploadFile = File(...)):
    """
    Direct video authenticity detection endpoint.
    Performs keyframe extraction, multi-frame aggregation, face analysis,
    temporal jitter estimation, and cross-modal acoustic forensics.
    Returns overall prediction, calibrated confidence, suspicious timestamps,
    frame-level predictions, and visual explanations.
    """
    import tempfile, os
    from fastapi import HTTPException
    from .services.ai_service import run_video_inference
    from .services.exceptions import AIServiceError

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty video file provided.")

    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="deepguard_video_")
    os.close(fd)

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        result = run_video_inference(temp_path)

        prob_real = result.probabilities.get("authentic", 0.0)
        prob_fake = result.probabilities.get("deepfake", 0.0)
        pred_class = 1 if result.prediction == "synthetic" else (0 if result.prediction == "authentic" else -1)
        label = "Fake" if pred_class == 1 else ("Real" if pred_class == 0 else "Uncertain")

        # Format frame-level predictions and visual explanations
        frame_preds = []
        visual_explanations = []
        for f in getattr(result, "frame_evidences", []):
            frame_dict = {
                "frame_index": f.frame_index,
                "timestamp_seconds": f.timestamp_seconds,
                "prediction": getattr(f, "prediction", "synthetic" if f.manipulation_score >= 0.38 else "authentic"),
                "manipulation_score": f.manipulation_score,
                "is_suspicious": getattr(f, "is_suspicious", f.manipulation_score >= 0.35),
                "primary_bbox": f.primary_bbox,
                "morphing_score": getattr(f, "morphing_score", None),
                "explanation": getattr(f, "explanation", None)
            }
            frame_preds.append(frame_dict)
            if frame_dict["is_suspicious"]:
                visual_explanations.append({
                    "timestamp_seconds": f.timestamp_seconds,
                    "frame_number": f.frame_index,
                    "manipulation_score": f.manipulation_score,
                    "bounding_box": f.primary_bbox,
                    "description": frame_dict["explanation"],
                    "severity": "critical" if f.manipulation_score >= 0.75 else "high"
                })

        return {
            "prediction": pred_class,
            "overall_prediction": label,
            "label": label,
            "verdict": result.prediction,
            "confidence": result.confidence,
            "calibrated_confidence": result.confidence,
            "probabilities": result.probabilities,
            "real_probability": prob_real,
            "fake_probability": prob_fake,
            "risk_level": result.risk_level,
            "duration_seconds": getattr(result, "duration_seconds", None),
            "total_frames_sampled": len(frame_preds),
            "suspicious_timestamps": getattr(result, "suspicious_timestamps", []),
            "suspicious_frames_count": len(getattr(result, "suspicious_timestamps", [])),
            "face_manipulation_score": result.face_manipulation_score,
            "temporal_inconsistency_score": result.temporal_inconsistency_score,
            "morphing_score": result.morphing_score,
            "audio_spoof_score": result.voice_cloning_score,
            "frame_level_predictions": frame_preds,
            "visual_explanations": visual_explanations,
            "indicators": [
                {
                    "type": ind.indicator_type,
                    "description": ind.description,
                    "severity": ind.severity,
                    "region_x": ind.region_x,
                    "region_y": ind.region_y,
                    "region_w": ind.region_w,
                    "region_h": ind.region_h,
                }
                for ind in result.indicators
            ],
            "inference_time_ms": round(result.processing_time_seconds * 1000, 2),
            "model_name": result.model_name,
            "model_version": result.model_version
        }

    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video inference failed: {exc}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.post("/detect-audio", summary="Direct AI Audio Detection")
@app.post("/api/v1/ai/detect-audio", summary="Direct AI Audio Detection")
@app.post("/api/v1/ai/predict-audio", summary="Direct AI Audio Detection")
async def detect_audio(file: UploadFile = File(...)):
    """
    Direct audio authenticity detection endpoint.
    Performs AASIST neural vocoder analysis, acoustic tampering detection,
    splicing detection, replay attack analysis, and voice cloning evaluation.
    Returns overall prediction, calibrated confidence, probabilities,
    tampering scores, splice points, and forensic indicators.
    """
    import tempfile, os
    from fastapi import HTTPException
    from .services.ai_service import run_audio_inference
    from .services.exceptions import AIServiceError

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file provided.")

    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="deepguard_audio_")
    os.close(fd)

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        result = run_audio_inference(temp_path)

        prob_real = result.probabilities.get("authentic", 0.0)
        prob_fake = result.probabilities.get("synthetic", 0.0)
        pred_class = 1 if result.prediction == "synthetic" else (0 if result.prediction == "authentic" else -1)
        label = "Fake" if pred_class == 1 else ("Real" if pred_class == 0 else "Uncertain")

        return {
            "prediction": pred_class,
            "overall_prediction": label,
            "label": label,
            "verdict": result.prediction,
            "confidence": result.confidence,
            "calibrated_confidence": result.confidence,
            "probabilities": result.probabilities,
            "real_probability": prob_real,
            "fake_probability": prob_fake,
            "risk_level": result.risk_level,
            "voice_cloning_score": getattr(result, "voice_cloning_score", 0.0),
            "spectral_anomaly_score": getattr(result, "spectral_anomaly_score", 0.0),
            "splicing_score": getattr(result, "splicing_score", 0.0),
            "replay_attack_score": getattr(result, "replay_attack_score", 0.0),
            "splice_points": getattr(result, "splice_points", []),
            "indicators": [
                {
                    "type": ind.indicator_type,
                    "description": ind.description,
                    "severity": ind.severity,
                }
                for ind in result.indicators
            ],
            "inference_time_ms": round(result.processing_time_seconds * 1000, 2),
            "model_name": result.model_name,
            "model_version": result.model_version,
            "evidence_category": getattr(result, "evidence_category", "INCONCLUSIVE"),
            "limitations": getattr(result, "limitations", []),
        }

    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio inference failed: {exc}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass



