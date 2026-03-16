#!/usr/bin/env bash

echo "Starting Streamlit..."
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 &

echo "Starting FastAPI..."
uvicorn backend.main:app --host 0.0.0.0 --port 10000