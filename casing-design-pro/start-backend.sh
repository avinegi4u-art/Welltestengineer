#!/usr/bin/env bash
cd "$(dirname "$0")/backend"
pip install -q -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
