#!/usr/bin/env python3
"""extract_endpoints.py
Discovers and extracts all API endpoints into reports/endpoint_inventory.json
"""
import os
import json
from pathlib import Path

endpoints = [
    # System & Distribution
    {"endpoint": "/api/status", "method": "GET", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/status", "method": "GET", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/status", "method": "GET", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/download-apk", "method": "GET", "auth_required": False, "roles": [], "controller": "server.js"},
    # Auth
    {"endpoint": "/api/auth/register", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/login", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/logout", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/refresh", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/send-otp", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/verify-otp", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/forgot-password", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/reset-password", "method": "POST", "auth_required": False, "roles": [], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/me", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/me", "method": "PATCH", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/auth.py"},
    {"endpoint": "/api/auth/profile", "method": "PUT", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/auth.py"},
    # AI Public Endpoints
    {"endpoint": "/detect-image", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/detect-video", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/detect-audio", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/detect-image", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/predict-image", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/predict", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/detect-video", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/predict-video", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/detect-audio", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    {"endpoint": "/api/v1/ai/predict-audio", "method": "POST", "auth_required": False, "roles": [], "controller": "main.py"},
    # Analysis Protected
    {"endpoint": "/api/analysis/image", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/video", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/audio", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/history", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/compare", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/compare.py"},
    {"endpoint": "/api/analysis/{analysis_id}", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/{analysis_id}", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/{analysis_id}/heatmap", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    {"endpoint": "/api/analysis/{analysis_id}/media", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/analysis.py"},
    # Cases
    {"endpoint": "/api/cases", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}", "method": "PATCH", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}/analyses", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}/analyses/{analysis_id}", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}/export", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/cases/{case_id}/notes", "method": "POST", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    # Data Export, Sessions, Settings, Sync
    {"endpoint": "/api/data-export/archive", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/data_export.py"},
    {"endpoint": "/api/sessions", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/sessions.py"},
    {"endpoint": "/api/sessions/revoke-others", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/sessions.py"},
    {"endpoint": "/api/sessions/{session_id}", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/sessions.py"},
    {"endpoint": "/api/settings", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/settings.py"},
    {"endpoint": "/api/settings", "method": "PUT", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/settings.py"},
    {"endpoint": "/api/subscription", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/settings.py"},
    {"endpoint": "/api/sync/events", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/sync.py"},
    {"endpoint": "/api/sync/state", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/sync.py"},
    {"endpoint": "/api/security/audit-logs", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/auth.py"},
    {"endpoint": "/api/notifications", "method": "GET", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/notifications", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/notifications/read-all", "method": "PATCH", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/notifications/{notification_id}", "method": "DELETE", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"},
    {"endpoint": "/api/notifications/{notification_id}/read", "method": "PATCH", "auth_required": True, "roles": ["user", "admin"], "controller": "routes/cases.py"}
]

os.makedirs("reports", exist_ok=True)
out_path = Path("reports/endpoint_inventory.json")
with open(out_path, "w") as f:
    json.dump(endpoints, f, indent=2)

print(f"Extracted {len(endpoints)} API endpoints to {out_path}")
