<div align="center">

# 🩺 Psoriasis Agent

### A Full-Stack, ML-Powered Health Tracking & Flare Prediction System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Psoriasis Agent** is a comprehensive health analytics application designed to help individuals with psoriasis and psoriatic arthritis track daily symptoms, analyze trends, and predict flare risks using machine learning.

[Features](#-features) • [Tech Stack](#-tech-stack) • [Setup](#-setup-instructions) • [Screenshots](#-screenshots) • [Future Scope](#-future-scope) • [License](#-license)

</div>

---

## 🌟 Features

<table>
<tr>
<td width="50%">

### 📊 Health Tracking
- **Daily symptom logging** with 10+ health metrics
- **Weekly & monthly** health summaries
- **Interactive visualizations** with trend analysis
- **SQLite database** for local data storage

</td>
<td width="50%">

### 🤖 Machine Learning
- **Flare risk prediction** using Logistic Regression
- **Risk level classification** (LOW/MEDIUM/HIGH)
- **Key factor identification** for flare triggers
- **Color-coded risk bands** for visual analysis

</td>
</tr>
</table>

---

## 📸 Screenshots

<div align="center">

### Daily Symptom Tracking
<img src="screenshots/DailyEntries.png" alt="Daily Entries Table" width="90%">

*Track and view all your daily health entries in an organized table format*

<br><br>

### Add New Entry
<img src="screenshots/Entry.png" alt="Add Entry Form" width="90%">

*Intuitive form to log daily symptoms with interactive sliders*

<br><br>

### Flare Risk Prediction
<img src="screenshots/FlareRiskPrediction.png" alt="Flare Risk Prediction" width="45%">

*ML-powered prediction showing probability and key risk factors*

<br><br>

### Symptom Trend Analysis
<img src="screenshots/SymptomTrends.png" alt="Symptom Trends" width="90%">

*Visual trends with color-coded risk bands to identify patterns*

</div>

---

## 🛠️ Tech Stack

<table>
<tr>
<td valign="top" width="50%">

### Backend
```
🐍 Python
⚡ FastAPI
🗄️ SQLAlchemy
💾 SQLite
🤖 Scikit-Learn
📊 Pandas
```

</td>
<td valign="top" width="50%">

### Frontend
```
🎨 Streamlit
📈 Plotly
🌐 Requests
```

</td>
</tr>
</table>

---

## 📁 Project Structure

```
psoriasis-agent/
│
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── entries.py
│   │   │   └── ml.py
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── ml_model.py
│   ├── seeddata.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   └── app.py
│
├── screenshots/
│   ├── DailyEntries.png
│   ├── Entry.png
│   ├── FlareRiskPrediction.png
│   └── SymptomTrends.png
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/ARYANBHAT-eng/psoriasis-agent.git
cd psoriasis-agent
```

### 2️⃣ Backend Setup

<details>
<summary><b>Click to expand backend setup</b></summary>

#### Create Virtual Environment (Recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Start Backend Server
```bash
uvicorn main:app --reload
```

✅ **Backend URL:** `http://127.0.0.1:8000`  
📚 **API Docs:** `http://127.0.0.1:8000/docs`

</details>

### 3️⃣ Database Initialization

The SQLite database (`psoriasis.db`) is automatically created when the backend starts.

#### Optional: Seed Sample Data

```bash
python seeddata.py
```

**Expected output:** `✓ Seed data inserted successfully`

### 4️⃣ Train Machine Learning Model

Before predictions work, train the ML model:

**Option A: Using API**
```bash
POST http://127.0.0.1:8000/ml/train
```

**Option B: Using Swagger UI**
- Navigate to `http://127.0.0.1:8000/docs`
- Find `/ml/train` endpoint
- Click "Try it out" → "Execute"

**Successful Response:**
```json
{
  "status": "trained",
  "samples": 30
}
```

### 5️⃣ Frontend (Streamlit Dashboard)

```bash
cd frontend
streamlit run app.py
```

🎨 **Dashboard URL:** `http://localhost:8501`

### 6️⃣ Production Deployment (Render)

This repository is configured for **two Render services** using `render.yaml`:

- `psoriasis-api` (FastAPI backend)
- `psoriasis-ui` (Streamlit frontend)

Both services are pinned to **Python 3.11.9** using `runtime.txt` and `PYTHON_VERSION` env vars.

#### Environment Variables

Backend (`psoriasis-api`):
- `DATABASE_URL` (defaults to local SQLite if omitted)
- `ALLOWED_ORIGINS` (comma-separated explicit frontend URLs — wildcard `*` is rejected by the backend)

Frontend (`psoriasis-ui`):
- `API_BASE_URL` (your deployed backend URL)

#### Local Install (split dependencies)

Backend:
```bash
pip install -r backend/requirements.txt
```

Frontend:
```bash
pip install -r frontend/requirements.txt
```

---

## 📊 Dashboard Capabilities

| Feature | Description |
|---------|-------------|
| ➕ **Add Entries** | Log daily symptoms with interactive sliders |
| 📅 **View Toggle** | Switch between weekly and monthly views |
| 📈 **Health Summary** | View key health metrics at a glance |
| 🎨 **Trend Analysis** | Color-coded risk bands for symptom patterns |
| 🤖 **ML Prediction** | Get flare risk probability and key factors |
| 🔍 **Risk Factors** | Identify what's contributing to flare risk |

---

## 🤖 Machine Learning Overview

<table>
<tr>
<td width="33%">

### Model
**Logistic Regression**
- Binary classification
- Probabilistic output
- Interpretable results

</td>
<td width="33%">

### Features (10)
- Itch intensity
- Redness level
- Scaling severity
- Joint pain
- Fatigue level
- Stress level
- Sleep quality
- Diet quality
- Missed medication
- Topical applied

</td>
<td width="33%">

### Output
**Flare Prediction**
- Probability (0-100%)
- Risk Level:
  - 🟢 LOW
  - 🟡 MEDIUM
  - 🔴 HIGH
- Key contributing factors

</td>
</tr>
</table>

---

## 🗺️ Future Scope

> Every item in this roadmap emerged from real gaps identified during design and from 14 years of lived experience managing psoriasis and psoriatic arthritis. This is not a feature wishlist — it is a deliberate evolution path from a personal symptom tracker toward a clinically meaningful health companion.

---

### 1️⃣ Infrastructure & Data Reliability

#### 🗄️ Migrate to Persistent Database (PostgreSQL)
SQLite on Render's free tier is ephemeral — data and the trained model can be lost on redeploys or restarts. For a chronic disease tracker where continuity of history is the entire value, this is a critical gap.

- Migrate backend to PostgreSQL (Render Postgres or Supabase free tier)
- Introduce database migration management via Alembic
- Add automated daily backup snapshots

#### 💾 Model Persistence & Graceful Degradation
Currently, `model.pkl` is generated at runtime and not committed to version control. After any clean deploy or service restart, the prediction endpoint becomes silently unavailable until `/ml/train` is manually re-triggered.

- Store the trained model artifact in a persistent object store (e.g., Cloudflare R2, AWS S3)
- Add a health check that detects a missing or stale model and surfaces a clear user-facing status
- Implement auto-retrain scheduling — weekly, or triggered automatically after N new entries are logged

---

### 2️⃣ Machine Learning — Toward Real Predictive Value

The current logistic regression on a single day's snapshot is a functional proof-of-concept. The following improvements would move predictions from coincidental to clinically meaningful.

#### ⏱️ Temporal Feature Engineering
Psoriasis and psoriatic arthritis flares are not caused by a single day's data — they are the result of compounding triggers over days. The model needs to see time.

- **Rolling averages**: 3-day, 7-day, 14-day windows for itch, redness, stress, and sleep
- **Lag features**: yesterday's and the day-before-yesterday's values as explicit inputs for today's prediction
- **Trend direction**: is a symptom score rising or falling over the past week?
- **Streak features**: consecutive days of missed medication, poor sleep, or high stress as dedicated signals

#### 🏷️ Better Flare Labeling
The current `psoriasis_flare` label is user-entered retrospectively — people tend to mark a flare only when symptoms are already severe. This teaches the model to predict obvious flares, not early-warning flares.

- Introduce a dedicated flare confirmation flow, separate from the daily logging form
- Explore algorithmically derived flare labels from symptom threshold crossings (e.g., composite score exceeding a rolling 14-day baseline by a configurable margin)
- Annotate label confidence so the model can weight high-certainty labels more strongly during training

#### 🦴 Separate Models for Psoriasis vs. Psoriatic Arthritis
Skin flares and joint inflammation (PsA) have different triggers, different lag times, and different clinically relevant features. A single model conflates two distinct conditions.

- Train separate prediction pipelines for skin flare risk and joint flare risk
- Add PsA-specific features: morning stiffness duration, affected joint count, functional limitation score
- Surface two independent risk scores in the dashboard

#### 📈 Model Upgrade Path

| Phase | Model | Trigger |
|-------|-------|---------|
| Current | Logistic Regression | Baseline (≥10 entries) |
| Near-term | Gradient Boosting (XGBoost/LightGBM) | ≥90 entries with cross-validation |
| Long-term | Temporal Fusion Transformer or LSTM | ≥6 months of consistent daily data |

- Display model confidence and data sufficiency warnings transparently to the user
- Enforce a minimum of 60–90 entries before any prediction is surfaced, with a clear progress indicator

---

### 3️⃣ Richer Data Model

Several well-documented psoriasis and PsA triggers are absent from the current data model:

| Feature | Clinical Rationale |
|---|---|
| 🌦️ Weather / humidity | Psoriasis has well-documented climate and humidity sensitivity |
| 🤒 Recent infections or illness | Common trigger, particularly for guttate psoriasis |
| 🍺 Alcohol intake | Established flare correlation across multiple studies |
| 🔄 Menstrual cycle phase | Significant hormonal flare trigger for many patients |
| 💊 Medication dose changes | Distinguishes adherence issues from intentional dose adjustments |
| 🦵 Specific joints affected | Clinically meaningful for PsA tracking beyond a single pain score |
| ⏰ Morning stiffness duration | Standard PsA clinical metric used in DAPSA scoring |
| ☀️ Phototherapy sessions | Common treatment modality worth correlating against outcomes |
| 🍽️ New food introductions | Enables user-defined dietary experiment tracking over time |

---

### 4️⃣ Logging Consistency & UX

Daily logging adherence is the lifeblood of this application. Without it, training data becomes selection-biased — people tend to log during flares and skip during good periods, which degrades model quality over time.

- **Daily reminders**: browser push notifications, or email/SMS via Twilio
- **Streak tracking**: logging consistency score visible on the dashboard
- **Quick-log mode**: a 30-second minimal entry for low-energy days — captures date, overall severity, and flare flag, and fills other fields with rolling averages to preserve data continuity
- **Context-aware prompts**: "Yesterday you logged high joint pain — how are your joints today?"

---

### 5️⃣ Clinician Sharing & Export

The core goal of this project is to help users have more informed conversations with clinicians. This currently has no artifact to support it.

- 📄 **PDF Report Export**: Weekly or monthly summary PDF formatted for clinical handoff — symptom trends, flare events, medication adherence, sleep and stress averages
- 🔗 **Shareable Read-Only Link**: Time-bounded, token-authenticated link to a read-only dashboard view for a clinician or caregiver
- 🏥 **FHIR-Compatible Export** *(long-term)*: Structured export in HL7 FHIR format for EHR integration

---

### 6️⃣ Authentication & Multi-User Support

Currently there is no authentication layer. This is acceptable for a local single-user demo but is a prerequisite for any shared or hosted deployment.

- JWT-based authentication (FastAPI Users or Auth0)
- Full per-user data isolation at the database level
- Optional caregiver or clinician accounts with read-only access to a patient's dashboard

---

### 7️⃣ Personalized Recommendations

The current recommendation engine is rule-based and generic. Telling someone who has managed a chronic condition for years that "your stress is high" is not actionable.

- Learn from the individual user's own history: which of *their* specific trigger combinations preceded *their* flares?
- Surface personalised pattern insights: *"Your last 3 flares all followed 2+ consecutive days of poor sleep combined with a missed medication day"*
- Distinguish between modifiable factors (stress, sleep, diet) and contextual ones (weather, illness)
- Allow users to add personal hypothesis tags to test their own suspected triggers over time

---

### 8️⃣ Testing & Observability

- Minimal API smoke test suite covering `/healthz`, `/entries`, summary, and prediction endpoints
- Structured logging with correlation IDs for request tracing across services
- Sentry integration for runtime error tracking and alerting
- Dashboard-level data quality warnings: insufficient entry count, long logging gaps, stale model artifact

---

## 💡 Origin & Motivation

This project was designed and built from scratch as an original idea, motivated by 14 years of living with psoriasis and 3 years with psoriatic arthritis. The goal was always practical: turn fragmented, hard-to-remember symptom history into structured data that is useful both for personal pattern recognition and for more informed conversations with clinicians.

Every architectural decision, every feature priority, and every item in the Future Scope above reflects a gap felt personally — not just observed technically.

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License - Free to use, modify, and distribute.
```

---

## 👨‍💻 Author

<div align="center">

**Aryan Bhat**

[![GitHub](https://img.shields.io/badge/GitHub-ARYANBHAT--eng-181717?style=for-the-badge&logo=github)](https://github.com/ARYANBHAT-eng)

---

### ⭐ Star this repo if you find it helpful!

Made with ❤️ for the psoriasis community

</div>