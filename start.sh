#!/usr/bin/env bash

PORT=${PORT:-10000}

echo "Starting Streamlit frontend..."
streamlit run frontend/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true &

echo "Starting FastAPI backend..."
cd backend
exec uvicorn main:app --host 0.0.0.0 --port $PORT