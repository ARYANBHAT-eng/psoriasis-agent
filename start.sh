#!/bin/bash

echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Starting FastAPI backend..."
cd backend
uvicorn main:app --host 0.0.0.0 --port $PORT &
cd ..

echo "Starting frontend..."
cd frontend
npm install
npm run dev -- --host 0.0.0.0

wait
