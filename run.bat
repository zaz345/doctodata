@echo off
chcp 65001 >nul
cd /d %~dp0
if not defined LLM_API_KEY (
  echo [!] LLM_API_KEY not set. Run:  setx LLM_API_KEY "your-key"
  echo     Then open a NEW terminal and run this again.
  pause
  exit /b 1
)
echo DocToData starting:  http://127.0.0.1:8642/docs
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8642
