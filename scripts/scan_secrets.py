#!/usr/bin/env python3
"""scan_secrets.py
Audits codebase files for secret patterns and writes reports/gitleaks.json
"""
import os
import json
import re
from pathlib import Path

reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

findings = []
secret_regex = re.compile(r"(?:api[_-]?key|secret|password)\s*[:=]\s*[\"']([A-Za-z0-9_\-]{24,})[\"']", re.I)

ignored_dirs = {".git", "node_modules", "dist", "build", ".venv", "__pycache__", ".gradle"}

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ignored_dirs]
    for file in files:
        if file.endswith((".py", ".js", ".ts", ".tsx", ".json", ".md")):
            p = os.path.join(root, file)
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = secret_regex.findall(content)
                    if matches:
                        findings.append({
                            "File": p,
                            "Description": "Potential hardcoded credential signature detected",
                            "Severity": "HIGH"
                        })
            except Exception:
                pass

out_file = reports_dir / "gitleaks.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

print(f"Secret scan audit completed. {len(findings)} records indexed to {out_file}")
