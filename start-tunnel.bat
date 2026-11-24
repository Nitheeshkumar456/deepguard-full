@echo off
echo Starting DeepGuard AI Permanent Tunnel...
if "%1"=="" (
    echo Usage: start-tunnel.bat ^<your-domain.ngrok-free.app^>
    .\tools\ngrok.exe http 8000
) else (
    .\tools\ngrok.exe http 8000 --domain=%1
)
