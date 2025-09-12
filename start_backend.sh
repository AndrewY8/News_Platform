#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd backend
python3 run.py
