import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models.auth import User, Session as UserSession
from app.models.analysis import Analysis, AnalysisResult, MediaType, AnalysisStatus, Prediction, RiskLevel
from app.models.investigation import InvestigationCase, CaseAnalysis, CaseNote
from app.utils.auth_utils import create_access_token
from app.utils.security import get_password_hash
from tests.conftest import TestingSessionLocal

@pytest.fixture(scope="module")
def test_investigator():
    db = TestingSessionLocal()
    # Clean up prior test runs
    db.query(CaseNote).delete()
    db.query(CaseAnalysis).delete()
    db.query(InvestigationCase).delete()
    db.query(UserSession).delete()
    db.query(User).filter(User.email == "forensic_lead@deepguard.ai").delete()
    db.commit()

    user = User(
        name="Chief Forensic Officer",
        email="forensic_lead@deepguard.ai",
        hashed_password=get_password_hash("InvestigationSecure123!"),
        is_active=True,
        is_verified=True,
        version=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    ctx = {
        "user_id": user.id,
        "token": token,
        "email": user.email,
        "headers": {"Authorization": f"Bearer {token}"}
    }
    db.close()
    return ctx

def test_investigation_case_workflow(test_investigator):
    client = TestClient(app)
    headers = test_investigator["headers"]
    user_id = test_investigator["user_id"]

    db = TestingSessionLocal()
    # 1. Create two mock analyses
    a1 = Analysis(
        user_id=user_id,
        media_type=MediaType.image,
        original_filename="suspect_evidence_1.jpg",
        status=AnalysisStatus.completed,
        created_at=datetime.utcnow()
    )
    a2 = Analysis(
        user_id=user_id,
        media_type=MediaType.image,
        original_filename="suspect_evidence_2.jpg",
        status=AnalysisStatus.completed,
        created_at=datetime.utcnow()
    )
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    r1 = AnalysisResult(
        analysis_id=a1.id,
        prediction=Prediction.synthetic,
        confidence=0.965,
        risk_level=RiskLevel.critical,
        model_name="FaceForensics++ DualPath-B0",
        face_manipulation_score=0.965,
    )
    r2 = AnalysisResult(
        analysis_id=a2.id,
        prediction=Prediction.authentic,
        confidence=0.88,
        risk_level=RiskLevel.low,
        model_name="FaceForensics++ DualPath-B0",
        face_manipulation_score=0.12,
    )
    db.add_all([r1, r2])
    db.commit()
    a1_id, a2_id = a1.id, a2.id
    db.close()

    # 2. Test create case
    create_res = client.post(
        "/api/cases",
        json={
            "title": "Operation DeepShield Redacted",
            "description": "Investigation into synthetic executive likeness on social channels.",
            "priority": "HIGH",
            "tags": "executive, deepfake, phishing",
            "initial_analysis_ids": [a1_id]
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    case_data = create_res.json()
    case_id = case_data["id"]
    assert case_data["title"] == "Operation DeepShield Redacted"
    assert case_data["status"] == "OPEN"
    assert len(case_data["analyses"]) == 1
    assert case_data["analyses"][0]["analysis_id"] == a1_id

    # 3. Test list cases
    list_res = client.get("/api/cases?priority=HIGH", headers=headers)
    assert list_res.status_code == 200
    cases_list = list_res.json()
    assert any(c["id"] == case_id for c in cases_list)

    # 4. Test attach second analysis
    attach_res = client.post(
        f"/api/cases/{case_id}/analyses",
        json={
            "analysis_id": a2_id,
            "notes": "Reference baseline comparison sample"
        },
        headers=headers,
    )
    assert attach_res.status_code == 200
    assert len(attach_res.json()["analyses"]) == 2

    # 5. Test add note
    note_res = client.post(
        f"/api/cases/{case_id}/notes",
        json={
            "content": "Spectral analysis confirms GAN blending artifacts around hairline."
        },
        headers=headers,
    )
    assert note_res.status_code == 200
    assert len(note_res.json()["notes"]) >= 1

    # 6. Test update case status
    patch_res = client.patch(
        f"/api/cases/{case_id}",
        json={
            "status": "FLAGGED",
            "priority": "CRITICAL"
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "FLAGGED"
    assert patch_res.json()["priority"] == "CRITICAL"

    # 7. Test export case dossier
    export_res = client.get(f"/api/cases/{case_id}/export", headers=headers)
    assert export_res.status_code == 200
    dossier = export_res.json()
    assert dossier["dossier_type"] == "DEEPGUARD_FORENSIC_INVESTIGATION_DOSSIER"
    assert len(dossier["evidence_chain"]) == 2
    assert len(dossier["chronological_notes"]) >= 1

    # 8. Test detach analysis
    detach_res = client.delete(f"/api/cases/{case_id}/analyses/{a2_id}", headers=headers)
    assert detach_res.status_code == 200
    assert len(detach_res.json()["analyses"]) == 1

    # 9. Test delete case (underlying analyses remain)
    del_res = client.delete(f"/api/cases/{case_id}", headers=headers)
    assert del_res.status_code == 200

    db2 = TestingSessionLocal()
    check_a1 = db2.query(Analysis).filter(Analysis.id == a1_id).first()
    assert check_a1 is not None
    db2.close()

def test_side_by_side_comparison(test_investigator):
    client = TestClient(app)
    headers = test_investigator["headers"]
    user_id = test_investigator["user_id"]

    db = TestingSessionLocal()
    a1 = Analysis(
        user_id=user_id,
        media_type=MediaType.image,
        original_filename="comparison_1.jpg",
        status=AnalysisStatus.completed,
    )
    a2 = Analysis(
        user_id=user_id,
        media_type=MediaType.image,
        original_filename="comparison_2.jpg",
        status=AnalysisStatus.completed,
    )
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    r1 = AnalysisResult(
        analysis_id=a1.id,
        prediction=Prediction.synthetic,
        confidence=0.92,
        risk_level=RiskLevel.critical,
        model_name="FaceForensics++ DualPath-B0",
    )
    r2 = AnalysisResult(
        analysis_id=a2.id,
        prediction=Prediction.authentic,
        confidence=0.85,
        risk_level=RiskLevel.low,
        model_name="FaceForensics++ DualPath-B0",
    )
    db.add_all([r1, r2])
    db.commit()
    a1_id, a2_id = a1.id, a2.id
    db.close()

    cmp_res = client.get(f"/api/analysis/compare?id1={a1_id}&id2={a2_id}", headers=headers)
    assert cmp_res.status_code == 200
    data = cmp_res.json()
    assert data["item1"]["id"] == a1_id
    assert data["item2"]["id"] == a2_id
    assert data["comparison"]["same_modality"] is True
    assert data["comparison"]["prediction_match"] is False
    assert "Discrepancy detected" in data["comparison"]["forensic_verdict"]

def test_sessions_and_audit_export(test_investigator):
    client = TestClient(app)
    headers = test_investigator["headers"]
    user_id = test_investigator["user_id"]

    db = TestingSessionLocal()
    # Add mock session
    sess = UserSession(
        user_id=user_id,
        token="test_mock_refresh_token_123",
        expires_at=datetime.utcnow() + timedelta(days=7),
        revoked=False,
        device_name="Chrome on Windows",
        platform="Windows",
        ip_address="127.0.0.1",
        last_active_at=datetime.utcnow()
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    sess_id = sess.id
    db.close()

    # 1. Test get active sessions
    sess_res = client.get("/api/sessions", headers=headers)
    assert sess_res.status_code == 200
    assert len(sess_res.json()) >= 1

    # 2. Test revoke session
    revoke_res = client.delete(f"/api/sessions/{sess_id}", headers=headers)
    assert revoke_res.status_code == 200

    # 3. Test get audit logs
    audit_res = client.get("/api/security/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1

    # 4. Test account data export archive
    export_res = client.get("/api/data-export/archive", headers=headers)
    assert export_res.status_code == 200
    archive = export_res.json()
    assert "profile" in archive
    assert archive["profile"]["email"] == test_investigator["email"]
    assert "scan_analyses" in archive
    assert "investigation_cases" in archive
    assert "security_audit_logs" in archive
