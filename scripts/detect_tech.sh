#!/usr/bin/env bash
# detect_tech.sh - Detect backend technology based on project files
# Sets BACKEND_TECH environment variable and outputs to GitHub Actions output

# Initialize variable
backend="unknown"

# Detect Java (Spring Boot, Maven/Gradle)
if ls *.pom.xml 2>/dev/null || ls build.gradle* 2>/dev/null; then
  backend="java"
fi

# Detect Node.js (package.json)
if [ -f package.json ]; then
  # Check for NestJS or Express
  if grep -q "@nestjs" package.json; then
    backend="node_nestjs"
  elif grep -q "express" package.json; then
    backend="node_express"
  else
    backend="node"
  fi
fi

# Detect Python (requirements.txt, pyproject.toml)
if [ -f requirements.txt ] || [ -f pyproject.toml ]; then
  # Check for Django or Flask or FastAPI
  if grep -q "Django" requirements.txt 2>/dev/null || grep -q "Django" pyproject.toml 2>/dev/null; then
    backend="python_django"
  elif grep -q "Flask" requirements.txt 2>/dev/null || grep -q "Flask" pyproject.toml 2>/dev/null; then
    backend="python_flask"
  elif grep -q "fastapi" requirements.txt 2>/dev/null || grep -q "fastapi" pyproject.toml 2>/dev/null; then
    backend="python_fastapi"
  else
    backend="python"
  fi
fi

# Detect .NET (csproj files)
if ls *.csproj 2>/dev/null; then
  backend="dotnet"
fi

# Detect Go (go.mod)
if [ -f go.mod ]; then
  backend="go"
fi

# Detect Ruby (Gemfile)
if [ -f Gemfile ]; then
  backend="ruby"
fi

# Export and output
echo "Detected backend technology: $backend"
# Set output for GitHub Actions
echo "backend_tech=$backend" >> $GITHUB_OUTPUT

# Also export as env var for subsequent steps
export BACKEND_TECH=$backend
