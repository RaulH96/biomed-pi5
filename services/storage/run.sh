#!/bin/bash
cd /home/harlink/biomed-pi5/services/storage
source /home/harlink/biomed-pi5/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
