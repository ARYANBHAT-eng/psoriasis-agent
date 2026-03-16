#!/usr/bin/env bash

echo "Starting Streamlit frontend..."
streamlit run frontend/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true &

echo "Starting FastAPI backend..."
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT