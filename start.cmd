@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8010
pause

