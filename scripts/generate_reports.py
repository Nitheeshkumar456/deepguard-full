#!/usr/bin/env python3
"""generate_reports.py
Generate security assessment reports from tool outputs.
Creates:
- reports/summary.md (markdown summary)
- reports/security-review.md (detailed findings)
- reports/executive-summary.md (executive summary)
- reports/dependency-report.md (dependency scan summary)
- reports/endpoint-inventory.xlsx (Excel with sheets for findings and endpoints)
"""
import json, os, sys
from pathlib import Path
import pandas as pd

# Ensure reports directory exists
reports_dir = Path('reports')
reports_dir.mkdir(exist_ok=True)

# Helper to load JSON safely
def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Load tool outputs
semgrep = load_json('reports/semgrep.json')
trivy = load_json('reports/trivy.json')
gitleaks = load_json('reports/gitleaks.json')
dep_check = load_json('reports/dependency-check.json')

# Consolidate findings into a DataFrame
findings = []
# Semgrep findings
for r in semgrep:
    findings.append({
        'Severity': r.get('severity', '').upper(),
        'Vulnerability Type': r.get('check_id', ''),
        'File Path': r.get('path', ''),
        'Endpoint': '',
        'Description': r.get('extra', {}).get('message', ''),
        'Impact': r.get('extra', {}).get('metadata', {}).get('impact', ''),
        'Recommended Fix': r.get('extra', {}).get('metadata', {}).get('fix', ''),
    })
# Trivy findings (vulnerabilities list)
for result in trivy:
    for vuln in result.get('Vulnerabilities', []):
        findings.append({
            'Severity': vuln.get('Severity', '').upper(),
            'Vulnerability Type': vuln.get('VulnerabilityID', ''),
            'File Path': result.get('Target', ''),
            'Endpoint': '',
            'Description': vuln.get('Title', ''),
            'Impact': vuln.get('Description', ''),
            'Recommended Fix': f"Update {vuln.get('PkgName', '')} to {vuln.get('FixedVersion', 'latest')}",
        })
# Gitleaks findings
for leak in gitleaks:
    findings.append({
        'Severity': 'HIGH',
        'Vulnerability Type': 'Hardcoded Secret',
        'File Path': leak.get('File', ''),
        'Endpoint': '',
        'Description': leak.get('Description', ''),
        'Impact': 'Credentials exposure',
        'Recommended Fix': 'Remove secret and rotate if used',
    })
# Dependency-Check findings (if any)
for dep in dep_check.get('dependencies', []):
    for vuln in dep.get('vulnerabilities', []):
        findings.append({
            'Severity': vuln.get('severity', '').upper(),
            'Vulnerability Type': vuln.get('name', ''),
            'File Path': dep.get('fileName', ''),
            'Endpoint': '',
            'Description': vuln.get('description', ''),
            'Impact': vuln.get('description', ''),
            'Recommended Fix': f"Upgrade {dep.get('fileName', '')} to a safe version",
        })

# Create DataFrames
findings_df = pd.DataFrame(findings)
# Fill missing columns
if 'Severity' not in findings_df.columns:
    findings_df['Severity'] = ''

# Write detailed markdown report
security_md_path = reports_dir / 'security-review.md'
with open(security_md_path, 'w') as f:
    f.write('# Security Review Findings\n\n')
    for _, row in findings_df.iterrows():
        f.write(f"## {row.get('Vulnerability Type', 'Finding')}\n")
        f.write(f"- **Severity:** {row.get('Severity', '')}\n")
        f.write(f"- **File Path:** {row.get('File Path', '')}\n")
        f.write(f"- **Endpoint:** {row.get('Endpoint', '')}\n")
        f.write(f"- **Description:** {row.get('Description', '')}\n")
        f.write(f"- **Impact:** {row.get('Impact', '')}\n")
        f.write(f"- **Recommended Fix:** {row.get('Recommended Fix', '')}\n\n")

# Executive summary
severity_counts = findings_df['Severity'].value_counts().to_dict()
summary_md_path = reports_dir / 'executive-summary.md'
with open(summary_md_path, 'w') as f:
    f.write('# Executive Summary\n\n')
    total = len(findings_df)
    f.write(f"**Total Findings:** {total}\n\n")
    for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = severity_counts.get(level, 0)
        f.write(f"- {level.title()}: {count}\n")
    f.write('\n')
    # Simple risk score (example weighting)
    score = max(0, 100 - (severity_counts.get('CRITICAL',0)*20 + severity_counts.get('HIGH',0)*10 + severity_counts.get('MEDIUM',0)*5))
    f.write(f"**Overall Security Score:** {score}/100\n")

# Dependency report (only if dep_check data exists)
if dep_check:
    dep_md_path = reports_dir / 'dependency-report.md'
    with open(dep_md_path, 'w') as f:
        f.write('# Dependency Vulnerability Report\n\n')
        for dep in dep_check.get('dependencies', []):
            if dep.get('vulnerabilities'):
                f.write(f"## {dep.get('fileName', '')}\n")
                for v in dep['vulnerabilities']:
                    f.write(f"- **{v.get('severity','').upper()}**: {v.get('name','')} - {v.get('description','')}\n")
                f.write('\n')

# Create Excel workbook with multiple sheets
excel_path = reports_dir / 'endpoint-inventory.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    # Sheet 1: Security Findings
    findings_df.to_excel(writer, sheet_name='Security Findings', index=False)
    # Sheet 2: Endpoint Inventory (placeholder – empty for now)
    pd.DataFrame(columns=['Endpoint','HTTP Method','Auth Required','Roles','Controller']).to_excel(writer, sheet_name='Endpoint Inventory', index=False)
    # Sheet 3: Dependency Vulnerabilities
    if dep_check:
        deps = []
        for dep in dep_check.get('dependencies', []):
            for v in dep.get('vulnerabilities', []):
                deps.append({
                    'Dependency': dep.get('fileName',''),
                    'Vulnerability': v.get('name',''),
                    'Severity': v.get('severity',''),
                    'Description': v.get('description',''),
                })
        pd.DataFrame(deps).to_excel(writer, sheet_name='Dependency Vulnerabilities', index=False)
    # Sheet 4: Risk Summary (same as executive summary)
    risk_summary = pd.DataFrame([
        {'Metric':'Total Findings','Value':total},
        {'Metric':'Critical','Value':severity_counts.get('CRITICAL',0)},
        {'Metric':'High','Value':severity_counts.get('HIGH',0)},
        {'Metric':'Medium','Value':severity_counts.get('MEDIUM',0)},
        {'Metric':'Low','Value':severity_counts.get('LOW',0)},
        {'Metric':'Security Score','Value':score},
    ])
    risk_summary.to_excel(writer, sheet_name='Risk Summary', index=False)

print('Report generation completed.')
