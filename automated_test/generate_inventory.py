import json
import os

endpoints = [
    # Public Authentication & System Endpoints
    {"method": "GET", "path": "/api/status", "expected_rule": "public", "category": "system"},
    {"method": "GET", "path": "/api/v1/status", "expected_rule": "public", "category": "system"},
    {"method": "GET", "path": "/api/v1/ai/status", "expected_rule": "public", "category": "system"},
    {"method": "GET", "path": "/download-apk", "expected_rule": "public", "category": "client-distribution"},
    {"method": "POST", "path": "/api/auth/register", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/login", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/logout", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/refresh", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/send-otp", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/verify-otp", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/forgot-password", "expected_rule": "public", "category": "auth"},
    {"method": "POST", "path": "/api/auth/reset-password", "expected_rule": "public", "category": "auth"},
    
    # Public AI Direct Inference Endpoints
    {"method": "POST", "path": "/api/v1/ai/detect-image", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/predict-image", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/predict", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/detect-image", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/detect-video", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/predict-video", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/detect-video", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/detect-audio", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/api/v1/ai/predict-audio", "expected_rule": "public", "category": "ai-inference"},
    {"method": "POST", "path": "/detect-audio", "expected_rule": "public", "category": "ai-inference"},

    # Protected User & Profile Endpoints
    {"method": "GET", "path": "/api/auth/me", "expected_rule": "requires-auth", "category": "user-profile"},
    {"method": "PATCH", "path": "/api/auth/me", "expected_rule": "requires-auth", "category": "user-profile"},
    {"method": "PUT", "path": "/api/auth/profile", "expected_rule": "requires-auth", "category": "user-profile"},

    # Protected Analysis Endpoints
    {"method": "POST", "path": "/api/analysis/image", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "POST", "path": "/api/analysis/video", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "POST", "path": "/api/analysis/audio", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "GET", "path": "/api/analysis/history", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "GET", "path": "/api/analysis/compare", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "GET", "path": "/api/analysis/{analysis_id}", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "DELETE", "path": "/api/analysis/{analysis_id}", "expected_rule": "requires-auth", "destructive": True, "category": "analysis"},
    {"method": "GET", "path": "/api/analysis/{analysis_id}/heatmap", "expected_rule": "requires-auth", "category": "analysis"},
    {"method": "GET", "path": "/api/analysis/{analysis_id}/media", "expected_rule": "requires-auth", "category": "analysis"},

    # Protected Case Management Endpoints
    {"method": "GET", "path": "/api/cases", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "POST", "path": "/api/cases", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "GET", "path": "/api/cases/{case_id}", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "PATCH", "path": "/api/cases/{case_id}", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "DELETE", "path": "/api/cases/{case_id}", "expected_rule": "requires-auth", "destructive": True, "category": "cases"},
    {"method": "POST", "path": "/api/cases/{case_id}/analyses", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "DELETE", "path": "/api/cases/{case_id}/analyses/{analysis_id}", "expected_rule": "requires-auth", "destructive": True, "category": "cases"},
    {"method": "GET", "path": "/api/cases/{case_id}/export", "expected_rule": "requires-auth", "category": "cases"},
    {"method": "POST", "path": "/api/cases/{case_id}/notes", "expected_rule": "requires-auth", "category": "cases"},

    # Protected Data Export
    {"method": "GET", "path": "/api/data-export/archive", "expected_rule": "requires-auth", "category": "data-export"},

    # Protected Notifications Endpoints
    {"method": "GET", "path": "/api/notifications", "expected_rule": "requires-auth", "category": "notifications"},
    {"method": "DELETE", "path": "/api/notifications", "expected_rule": "requires-auth", "destructive": True, "category": "notifications"},
    {"method": "PATCH", "path": "/api/notifications/read-all", "expected_rule": "requires-auth", "category": "notifications"},
    {"method": "DELETE", "path": "/api/notifications/{notification_id}", "expected_rule": "requires-auth", "destructive": True, "category": "notifications"},
    {"method": "PATCH", "path": "/api/notifications/{notification_id}/read", "expected_rule": "requires-auth", "category": "notifications"},

    # Protected Security & Audit Endpoints
    {"method": "GET", "path": "/api/security/audit-logs", "expected_rule": "requires-auth", "category": "security"},

    # Protected Sessions Endpoints
    {"method": "GET", "path": "/api/sessions", "expected_rule": "requires-auth", "category": "sessions"},
    {"method": "DELETE", "path": "/api/sessions/revoke-others", "expected_rule": "requires-auth", "category": "sessions"},
    {"method": "DELETE", "path": "/api/sessions/{session_id}", "expected_rule": "requires-auth", "category": "sessions"},

    # Protected Settings & Subscription Endpoints
    {"method": "GET", "path": "/api/settings", "expected_rule": "requires-auth", "category": "settings"},
    {"method": "PUT", "path": "/api/settings", "expected_rule": "requires-auth", "category": "settings"},
    {"method": "GET", "path": "/api/subscription", "expected_rule": "requires-auth", "category": "subscription"},

    # Protected Sync Endpoints
    {"method": "GET", "path": "/api/sync/events", "expected_rule": "requires-auth", "category": "sync"},
    {"method": "GET", "path": "/api/sync/state", "expected_rule": "requires-auth", "category": "sync"}
]

os.makedirs("automated_test", exist_ok=True)
with open("automated_test/discovered_endpoints.json", "w") as f:
    json.dump(endpoints, f, indent=2)

print(f"Saved {len(endpoints)} endpoints to automated_test/discovered_endpoints.json")

