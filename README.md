Psoriasis Agent
A Full-Stack, ML-Powered Health Tracking & Flare Prediction System

Psoriasis Agent is a full-stack health analytics application designed to help individuals with psoriasis and psoriatic arthritis track daily symptoms, analyze trends, and predict flare risks using machine learning.

The system combines structured daily health logging, backend REST APIs, machine learning–based flare prediction, and an interactive Streamlit dashboard.

FEATURES

Daily symptom tracking

Weekly and monthly health summaries

Machine learning–based flare risk prediction

Color-band risk trend visualization

SQLite local database

FastAPI backend

Streamlit interactive dashboard

TECH STACK

Backend:

Python

FastAPI

SQLAlchemy

SQLite

Scikit-Learn

Pandas

Frontend:

Streamlit

Plotly

Requests

PROJECT STRUCTURE

psoriasis-agent/

backend/
app/
routers/
entries.py
ml.py
crud.py
database.py
models.py
schemas.py
ml_model.py
seeddata.py
main.py
requirements.txt

frontend/
app.py

.gitignore
README.txt

SETUP INSTRUCTIONS

Clone the repository

git clone https://github.com/ARYANBHAT-eng/psoriasis-agent.git

cd psoriasis-agent

Backend setup

(Optional but recommended)
Create and activate virtual environment:

python -m venv venv
venv\Scripts\activate

Install dependencies:

cd backend
pip install -r requirements.txt

Start backend server

uvicorn main:app --reload

Backend URL:
http://127.0.0.1:8000

Swagger API Docs:
http://127.0.0.1:8000/docs

DATABASE INITIALIZATION

The SQLite database (psoriasis.db) is automatically created when the backend starts.

Optional but recommended: Seed sample data

A seeding script is included to populate the database with realistic entries.

Run:

python seeddata.py

Expected output:
Seed data inserted successfully

MACHINE LEARNING TRAINING

Before predictions can work, the ML model must be trained.

Train model using API:

POST http://127.0.0.1:8000/ml/train

You can also do this from Swagger UI.

Successful response example:

{
"status": "trained",
"samples": 30
}

FRONTEND (STREAMLIT DASHBOARD)

Start the frontend:

cd frontend
streamlit run app.py

Dashboard URL:
http://localhost:8501

DASHBOARD CAPABILITIES

Add daily symptom entries

Toggle between weekly and monthly views

View health summary cards

Analyze symptom trends with color-coded risk bands

Get ML-based flare risk prediction

View key contributing risk factors

MACHINE LEARNING OVERVIEW

Model:

Logistic Regression

Features:

Itch

Redness

Scaling

Joint pain

Fatigue

Stress level

Sleep quality

Diet quality

Missed medication

Topical applied

Target:

psoriasis_flare (0 or 1)

Outputs:

Probability of flare

Risk level (LOW / MEDIUM / HIGH)

Key contributing factors

ROADMAP / FUTURE WORK

Mobile application (React Native / Flutter)

User authentication

Cloud deployment

API key integration

Advanced ML models

Long-term flare forecasting

LICENSE

MIT License
Free to use, modify, and distribute.

AUTHOR

Aryan Bhat
GitHub: https://github.com/ARYANBHAT-eng
