#!/usr/bin/env bash
# detect_tech.sh - Detect backend technology based on project files
# Sets BACKEND_TECH environment variable and outputs to GitHub Actions output

backend="python_fastapi"

if [ -f backend/app/main.py ] || [ -f backend/requirements.txt ]; then
  backend="python_fastapi"
elif [ -f requirements.txt ] || [ -f pyproject.toml ]; then
  if grep -q "fastapi" requirements.txt 2>/dev/null || grep -q "fastapi" pyproject.toml 2>/dev/null; then
    backend="python_fastapi"
  elif grep -q "Django" requirements.txt 2>/dev/null; then
    backend="python_django"
  elif grep -q "Flask" requirements.txt 2>/dev/null; then
    backend="python_flask"
  else
    backend="python"
  fi
elif [ -f server/server.js ] || [ -f package.json ]; then
  backend="node_express"
fi

echo "Detected backend technology: $backend"

if [ -n "$GITHUB_OUTPUT" ]; then
  echo "backend_tech=$backend" >> "$GITHUB_OUTPUT"
fi

export BACKEND_TECH="$backend"
