import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date

# CONFIG
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Psoriasis Dashboard",
    layout="wide",
)

# HEADER
st.title("🧬 Psoriasis Personalized Agent")
st.caption("Daily tracking • Weekly insights • ML-powered flare prediction")

st.divider()
view_mode = st.radio(
    "📅 View Mode",
    options=["Weekly", "Monthly"],
    horizontal=True
)

if view_mode == "Weekly":
    weeks = 1
    days = 7
else:
    weeks = 4
    days = 30

# ADD DAILY ENTRY FORM
st.divider()
st.subheader("➕ Add Daily Entry")

with st.form("daily_entry_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)

    with c1:
        entry_date = st.date_input("Date", value=date.today())
        itch = st.slider("Itch", 0, 10, 5)
        redness = st.slider("Redness", 0, 10, 5)
        scaling = st.slider("Scaling", 0, 10, 5)

    with c2:
        joint_pain = st.slider("Joint Pain", 0, 10, 5)
        fatigue = st.slider("Fatigue", 0, 10, 5)
        stress_level = st.slider("Stress Level", 0, 10, 5)

    with c3:
        sleep_quality = st.slider("Sleep Quality", 0, 10, 5)
        diet_quality = st.slider("Diet Quality", 0, 10, 5)
        missed_medication = st.selectbox("Missed Medication?", [0, 1])
        topical_applied = st.selectbox("Topical Applied?", [0, 1])
        psoriasis_flare = st.selectbox("Flare Today?", [0, 1])

    notes = st.text_input("Notes")
    submitted = st.form_submit_button("Save Entry")

if submitted:
    payload = {
        "date": str(entry_date),
        "itch": itch,
        "redness": redness,
        "scaling": scaling,
        "joint_pain": joint_pain,
        "fatigue": fatigue,
        "stress_level": stress_level,
        "sleep_quality": sleep_quality,
        "diet_quality": diet_quality,
        "missed_medication": missed_medication,
        "topical_applied": topical_applied,
        "psoriasis_flare": psoriasis_flare,
        "notes": notes,
    }

    res = requests.post(f"{API_BASE}/entries", json=payload)
    if res.status_code == 200:
        st.success("✅ Entry saved successfully")
    else:
        st.error(res.text)

# LOAD DATA
entries_res = requests.get(f"{API_BASE}/entries")
if entries_res.status_code != 200:
    st.error("Failed to load entries")
    st.stop()

df = pd.DataFrame(entries_res.json())
if df.empty:
    st.info("No data available yet")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# DERIVED FEATURES
df["symptom_total"] = (
    df["itch"] +
    df["redness"] +
    df["scaling"] +
    df["joint_pain"] +
    df["fatigue"]
)

def risk_band(score):
    if score < 15:
        return "Low"
    elif score <= 25:
        return "Medium"
    return "High"

df["risk"] = df["symptom_total"].apply(risk_band)

# APPLY VIEW FILTER LAST
df_view = df.tail(days)

# WEEKLY / MONTHLY SUMMARY
st.divider()
st.subheader("📊 Summary")

summary_res = requests.get(
    f"{API_BASE}/entries/summary?weeks={weeks}"
)

if summary_res.status_code == 200:
    summary = summary_res.json()
    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Avg Symptom", round(summary["avg_symptom"], 2))
    k2.metric("Avg Sleep", round(summary["avg_sleep"], 2))
    k3.metric("Missed Med Days", summary["missed_med_days"])
    k4.metric("Avg Stress", round(summary["avg_stress"], 2))
    k5.metric("Latest Symptom", round(summary["latest_symptom_total"], 2))
else:
    st.warning("Summary not available")

# RISK TREND
st.divider()
st.subheader("📈 Symptom Trend with Risk Bands")

fig = px.scatter(
    df_view,
    x="date",
    y="symptom_total",
    color="risk",
    color_discrete_map={
        "Low": "#2ecc71",
        "Medium": "#f39c12",
        "High": "#e74c3c",
    },
    title=f"{view_mode} Symptom Trend",
)

fig.update_traces(mode="lines+markers")
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Symptom Score",
    height=450,
)

st.plotly_chart(fig, use_container_width=True)

# DAILY ENTRIES TABLE
st.divider()
st.subheader("📋 Daily Entries")

display_cols = [
    "date",
    "itch",
    "redness",
    "scaling",
    "joint_pain",
    "fatigue",
    "stress_level",
    "sleep_quality",
    "diet_quality",
    "missed_medication",
    "topical_applied",
    "psoriasis_flare",
    "notes",
]

st.dataframe(
    df_view[display_cols].sort_values("date", ascending=False),
    use_container_width=True,
)

# ML PREDICTION
st.divider()
st.subheader("🧠 Flare Risk Prediction")

pred_res = requests.get(f"{API_BASE}/ml/predict")

if pred_res.status_code == 200:
    pred = pred_res.json()

    st.metric(
        label="Probability of Flare",
        value=f"{pred['probability_of_flare']:.2%}",
    )

    st.write("**Risk Level:**", pred["risk_level"])
    st.write("**Key Factors:**")
    for f in pred["key_factors"]:
        st.write(f"• {f}")
else:
    st.warning("Model not trained yet")
