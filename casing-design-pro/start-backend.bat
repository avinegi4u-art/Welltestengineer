@echo off
cd /d "%~dp0backend"
python -m pip install -q -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
