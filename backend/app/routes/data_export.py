import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.analysis import Analysis
from ..models.investigation import InvestigationCase
from ..models.security import SecurityAuditLog
from ..models.settings import UserSettings
from ..services.audit_service import log_security_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-export-and-security"])

class AuditLogItemResponse(BaseModel):
    id: int
    action: str
    status: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

@router.get("/api/security/audit-logs", response_model=List[AuditLogItemResponse])
def get_security_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve paginated security and data governance audit logs for current user."""
    logs = db.query(SecurityAuditLog).filter(
        SecurityAuditLog.user_id == current_user.id
    ).order_by(desc(SecurityAuditLog.created_at)).offset(offset).limit(limit).all()

    return logs

@router.get("/api/data-export/archive")
def export_user_data_archive(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and download a comprehensive, GDPR-compliant JSON archive of all
    user account data, scan records, investigation cases, and security audit history.
    """
    # 1. Profile
    profile_data = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
    }

    # 2. Settings
    settings_record = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    settings_data = {
        "theme": settings_record.theme if settings_record else "dark",
        "sensitivity": settings_record.sensitivity if settings_record else 0.5,
        "auto_delete_history": settings_record.auto_delete_history if settings_record else False,
        "email_notifications": settings_record.email_notifications if settings_record else True,
        "push_notifications": settings_record.push_notifications if settings_record else True,
    } if settings_record else {}

    # 3. Analyses
    analyses_records = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()
    analyses_data = []
    for a in analyses_records:
        r = a.result
        indicators = [
            {
                "type": ind.indicator_type,
                "severity": ind.severity.value if hasattr(ind.severity, "value") else str(ind.severity),
                "description": ind.description,
                "timestamp_seconds": ind.timestamp_seconds,
                "frame_number": ind.frame_number,
            }
            for ind in a.indicators
        ]
        analyses_data.append({
            "id": a.id,
            "original_filename": a.original_filename,
            "media_type": a.media_type.value if hasattr(a.media_type, "value") else str(a.media_type),
            "file_size": a.file_size,
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "prediction": r.prediction.value if r and hasattr(r.prediction, "value") else None,
            "confidence": r.confidence if r else None,
            "risk_level": r.risk_level.value if r and hasattr(r.risk_level, "value") else None,
            "indicators": indicators,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # 4. Investigation Cases
    cases_records = db.query(InvestigationCase).filter(InvestigationCase.user_id == current_user.id).all()
    cases_data = []
    for c in cases_records:
        cases_data.append({
            "case_number": c.case_number,
            "title": c.title,
            "description": c.description,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "priority": c.priority.value if hasattr(c.priority, "value") else str(c.priority),
            "tags": c.tags,
            "linked_analyses_count": len(c.case_analyses),
            "notes": [
                {
                    "author": n.author_name,
                    "content": n.content,
                    "created_at": n.created_at.isoformat(),
                }
                for n in c.notes
            ],
            "created_at": c.created_at.isoformat(),
        })

    # 5. Audit Logs
    audit_records = db.query(SecurityAuditLog).filter(SecurityAuditLog.user_id == current_user.id).all()
    audit_data = [
        {
            "action": al.action,
            "status": al.status,
            "ip_address": al.ip_address,
            "details": al.details,
            "timestamp": al.created_at.isoformat(),
        }
        for al in audit_records
    ]

    export_payload = {
        "export_metadata": {
            "platform": "DeepGuard AI Multimodal Authenticity Platform",
            "version": "1.0.0",
            "exported_at": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
        },
        "profile": profile_data,
        "preferences_and_settings": settings_data,
        "scan_analyses": analyses_data,
        "investigation_cases": cases_data,
        "security_audit_logs": audit_data,
    }

    # Log security event
    log_security_event(
        db=db,
        user_id=current_user.id,
        action="DATA_EXPORT",
        details="Exported full GDPR account archive",
        request=request
    )

    json_str = json.dumps(export_payload, indent=2)
    filename = f"deepguard_account_export_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
