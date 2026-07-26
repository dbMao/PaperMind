@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================
echo   PaperMind
echo   Backend : http://127.0.0.1:8000
echo   Frontend: http://localhost:3000
echo ========================================

start "PaperMind-Backend" cmd /k "chcp 65001 >nul && cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
start "PaperMind-Frontend" cmd /k "chcp 65001 >nul && cd /d %~dp0frontend && npm run dev"

echo Services starting...
pause
