#!/bin/bash
cd apps/api
../../venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
