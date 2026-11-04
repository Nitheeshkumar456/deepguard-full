import logging
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..dependencies import get_db, get_current_user
from ..models.auth import User
from ..models.analysis import Analysis, AnalysisResult, AnalysisIndicator
from ..models.investigation import (
    InvestigationCase,
    CaseAnalysis,
    CaseNote,
    CaseStatus,
    CasePriority,
)
from ..services.audit_service import log_security_event
from ..services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["investigations"])

# ── Schemas ──
class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=256)
    description: Optional[str] = None
    priority: Optional[CasePriority] = CasePriority.MEDIUM
    tags: Optional[str] = None
    initial_analysis_ids: Optional[List[int]] = None

class CaseUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=256)
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    tags: Optional[str] = None

class AddAnalysisRequest(BaseModel):
    analysis_id: int
    notes: Optional[str] = None

class AddNoteRequest(BaseModel):
    content: str = Field(..., min_length=1)

class CaseNoteResponse(BaseModel):
    id: int
    author_name: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

class CaseAnalysisItemResponse(BaseModel):
    id: int
    analysis_id: int
    notes: Optional[str]
    added_at: datetime
    media_type: str
    original_filename: str
    prediction: Optional[str]
    confidence: Optional[float]
    risk_level: Optional[str]

class CaseSummaryResponse(BaseModel):
    id: int
    case_number: str
    title: str
    description: Optional[str]
    status: CaseStatus
    priority: CasePriority
    tags: Optional[str]
    analyses_count: int
    notes_count: int
    created_at: datetime
    updated_at: datetime

class CaseDetailResponse(BaseModel):
    id: int
    case_number: str
    title: str
    description: Optional[str]
    status: CaseStatus
    priority: CasePriority
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime
    analyses: List[CaseAnalysisItemResponse]
    notes: List[CaseNoteResponse]

def generate_case_number() -> str:
    year = datetime.utcnow().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CASE-{year}-{suffix}"

@router.get("", response_model=List[CaseSummaryResponse])
def list_cases(
    status: Optional[CaseStatus] = None,
    priority: Optional[CasePriority] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all investigation cases for current user with optional filtering."""
    query = db.query(InvestigationCase).filter(InvestigationCase.user_id == current_user.id)

    if status:
        query = query.filter(InvestigationCase.status == status)
    if priority:
        query = query.filter(InvestigationCase.priority == priority)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (InvestigationCase.title.ilike(search_fmt)) |
            (InvestigationCase.case_number.ilike(search_fmt)) |
            (InvestigationCase.tags.ilike(search_fmt))
        )

    cases = query.order_by(desc(InvestigationCase.updated_at)).all()

    results = []
    for c in cases:
        results.append(
            CaseSummaryResponse(
                id=c.id,
                case_number=c.case_number,
                title=c.title,
                description=c.description,
                status=c.status,
                priority=c.priority,
                tags=c.tags,
                analyses_count=len(c.case_analyses),
                notes_count=len(c.notes),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return results

@router.post("", response_model=CaseDetailResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new investigation case and optionally attach existing analyses."""
    new_case = InvestigationCase(
        case_number=generate_case_number(),
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        status=CaseStatus.OPEN,
        priority=payload.priority or CasePriority.MEDIUM,
        tags=payload.tags,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Attach initial analyses if provided
    if payload.initial_analysis_ids:
        for aid in payload.initial_analysis_ids:
            # Verify user ownership of analysis
            analysis = db.query(Analysis).filter(
                Analysis.id == aid,
                Analysis.user_id == current_user.id
            ).first()
            if analysis:
                assoc = CaseAnalysis(
                    case_id=new_case.id,
                    analysis_id=analysis.id,
                    notes="Initial attachment on case creation"
                )
                db.add(assoc)
        db.commit()
        db.refresh(new_case)

    # Log audit event
    log_security_event(
        db=db,
        user_id=current_user.id,
        action="CASE_CREATE",
        details=f"Created case {new_case.case_number} ('{new_case.title}')",
        request=request
    )

    # Broadcast WebSocket update
    try:
        ws_manager.broadcast_to_user_sync(
            current_user.id,
            {
                "type": "case.created",
                "case_id": new_case.id,
                "case_number": new_case.case_number,
                "title": new_case.title,
                "status": new_case.status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as exc:
        logger.debug(f"WS notification note: {exc}")

    return get_case_detail(new_case.id, current_user, db)

@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full details of a specific investigation case."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation case not found"
        )

    # Format analyses
    analyses_list = []
    for ca in case.case_analyses:
        analysis = ca.analysis
        if analysis:
            res = analysis.result
            analyses_list.append(
                CaseAnalysisItemResponse(
                    id=ca.id,
                    analysis_id=analysis.id,
                    notes=ca.notes,
                    added_at=ca.added_at,
                    media_type=analysis.media_type.value if hasattr(analysis.media_type, "value") else str(analysis.media_type),
                    original_filename=analysis.original_filename,
                    prediction=res.prediction.value if res and hasattr(res.prediction, "value") else (str(res.prediction) if res else None),
                    confidence=res.confidence if res else None,
                    risk_level=res.risk_level.value if res and hasattr(res.risk_level, "value") else (str(res.risk_level) if res else None),
                )
            )

    # Format notes
    notes_list = [
        CaseNoteResponse(
            id=n.id,
            author_name=n.author_name,
            content=n.content,
            created_at=n.created_at,
        )
        for n in case.notes
    ]

    return CaseDetailResponse(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        description=case.description,
        status=case.status,
        priority=case.priority,
        tags=case.tags,
        created_at=case.created_at,
        updated_at=case.updated_at,
        analyses=analyses_list,
        notes=notes_list,
    )

@router.patch("/{case_id}", response_model=CaseDetailResponse)
def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update case metadata, status, priority, or tags."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation case not found"
        )

    if payload.title is not None:
        case.title = payload.title
    if payload.description is not None:
        case.description = payload.description
    if payload.status is not None:
        case.status = payload.status
    if payload.priority is not None:
        case.priority = payload.priority
    if payload.tags is not None:
        case.tags = payload.tags

    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    # WebSocket sync broadcast
    try:
        ws_manager.broadcast_to_user_sync(
            current_user.id,
            {
                "type": "case.updated",
                "case_id": case.id,
                "case_number": case.case_number,
                "status": case.status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as exc:
        logger.debug(f"WS notification note: {exc}")

    return get_case_detail(case.id, current_user, db)

@router.post("/{case_id}/analyses", response_model=CaseDetailResponse)
def attach_analysis_to_case(
    case_id: int,
    payload: AddAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link an existing media analysis to this investigation case."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    # Verify analysis ownership
    analysis = db.query(Analysis).filter(
        Analysis.id == payload.analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis record not found")

    # Check if already attached
    existing = db.query(CaseAnalysis).filter(
        CaseAnalysis.case_id == case.id,
        CaseAnalysis.analysis_id == analysis.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This analysis is already attached to this case")

    assoc = CaseAnalysis(
        case_id=case.id,
        analysis_id=analysis.id,
        notes=payload.notes,
    )
    db.add(assoc)
    case.updated_at = datetime.utcnow()
    db.commit()

    return get_case_detail(case.id, current_user, db)

@router.delete("/{case_id}/analyses/{analysis_id}", response_model=CaseDetailResponse)
def detach_analysis_from_case(
    case_id: int,
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink an analysis from this investigation case."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    assoc = db.query(CaseAnalysis).filter(
        CaseAnalysis.case_id == case.id,
        CaseAnalysis.analysis_id == analysis_id
    ).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Analysis is not attached to this case")

    db.delete(assoc)
    case.updated_at = datetime.utcnow()
    db.commit()

    return get_case_detail(case.id, current_user, db)

@router.post("/{case_id}/notes", response_model=CaseDetailResponse)
def add_case_note(
    case_id: int,
    payload: AddNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a timestamped investigator note to the case."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    note = CaseNote(
        case_id=case.id,
        user_id=current_user.id,
        author_name=current_user.name or current_user.email,
        content=payload.content.strip(),
    )
    db.add(note)
    case.updated_at = datetime.utcnow()
    db.commit()

    return get_case_detail(case.id, current_user, db)

@router.delete("/{case_id}", status_code=status.HTTP_200_OK)
def delete_case(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an investigation case without deleting the underlying analyses."""
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    case_num = case.case_number
    db.delete(case)
    db.commit()

    log_security_event(
        db=db,
        user_id=current_user.id,
        action="CASE_DELETE",
        details=f"Deleted case {case_num}",
        request=request
    )

    try:
        ws_manager.broadcast_to_user_sync(
            current_user.id,
            {
                "type": "case.deleted",
                "case_id": case_id,
                "case_number": case_num,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as exc:
        logger.debug(f"WS notification note: {exc}")

    return {"message": f"Case {case_num} has been successfully deleted."}

@router.get("/{case_id}/export")
def export_case_dossier(
    case_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and export a comprehensive forensic case dossier in structured JSON format.
    Includes chain of custody, model versions, all attached media indicators, and investigator notes.
    """
    case = db.query(InvestigationCase).filter(
        InvestigationCase.id == case_id,
        InvestigationCase.user_id == current_user.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Investigation case not found")

    attached_evidence = []
    for ca in case.case_analyses:
        a = ca.analysis
        res = a.result if a else None
        indicators = [
            {
                "type": ind.indicator_type,
                "severity": ind.severity.value if hasattr(ind.severity, "value") else str(ind.severity),
                "description": ind.description,
                "timestamp_seconds": ind.timestamp_seconds,
                "frame_number": ind.frame_number,
            }
            for ind in (a.indicators if a else [])
        ]

        attached_evidence.append({
            "analysis_id": a.id,
            "filename": a.original_filename,
            "media_type": a.media_type.value if hasattr(a.media_type, "value") else str(a.media_type),
            "file_size_bytes": a.file_size,
            "prediction": res.prediction.value if res and hasattr(res.prediction, "value") else None,
            "confidence": res.confidence if res else None,
            "risk_level": res.risk_level.value if res and hasattr(res.risk_level, "value") else None,
            "model_name": res.model_name if res else None,
            "model_version": res.model_version if res else None,
            "indicators": indicators,
            "investigator_item_notes": ca.notes,
            "attached_at": ca.added_at.isoformat(),
        })

    notes_export = [
        {
            "id": n.id,
            "author": n.author_name,
            "content": n.content,
            "timestamp": n.created_at.isoformat(),
        }
        for n in case.notes
    ]

    dossier = {
        "dossier_type": "DEEPGUARD_FORENSIC_INVESTIGATION_DOSSIER",
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "status": case.status.value,
        "priority": case.priority.value,
        "tags": [t.strip() for t in case.tags.split(",") if t.strip()] if case.tags else [],
        "created_at": case.created_at.isoformat(),
        "exported_at": datetime.utcnow().isoformat(),
        "lead_investigator": {
            "name": current_user.name,
            "email": current_user.email,
        },
        "evidence_summary": {
            "total_items": len(attached_evidence),
            "synthetic_count": sum(1 for e in attached_evidence if e["prediction"] == "synthetic"),
            "authentic_count": sum(1 for e in attached_evidence if e["prediction"] == "authentic"),
            "uncertain_count": sum(1 for e in attached_evidence if e["prediction"] == "uncertain"),
        },
        "evidence_chain": attached_evidence,
        "chronological_notes": notes_export,
    }

    log_security_event(
        db=db,
        user_id=current_user.id,
        action="CASE_EXPORT",
        details=f"Exported forensic dossier for case {case.case_number}",
        request=request
    )

    return dossier
