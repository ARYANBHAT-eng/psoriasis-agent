import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date
import os

# CONFIG
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="Psoriasis Dashboard",
    layout="wide",
)


def _headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle_401(res) -> bool:
    if res.status_code == 401:
        st.session_state.pop("token", None)
        st.rerun()
    return res.status_code == 401


# AUTH GATE
if "token" not in st.session_state:
    try:
        status_res = requests.get(f"{API_BASE}/auth/setup", timeout=5)
        setup_done = status_res.json().get("setup_done", True)
    except Exception:
        st.error("Cannot connect to backend. Check that the API service is running.")
        st.stop()

    if not setup_done:
        st.subheader("Create Account")
        st.caption("Min 12 characters, at least one letter and one digit.")
        with st.form("signup"):
            uname = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                r = requests.post(
                    f"{API_BASE}/auth/setup",
                    json={"username": uname, "password": pwd},
                )
                if r.status_code == 201:
                    tok = requests.post(
                        f"{API_BASE}/auth/token",
                        data={"username": uname, "password": pwd},
                    )
                    st.session_state.token = tok.json()["access_token"]
                    st.rerun()
                else:
                    st.error(r.json().get("detail", r.text))
    else:
        st.subheader("Login")
        with st.form("login"):
            uname = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                r = requests.post(
                    f"{API_BASE}/auth/token",
                    data={"username": uname, "password": pwd},
                )
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Login failed."))

    st.stop()


# PROFILE FETCH (auto-creates with defaults on first read)
if "profile" not in st.session_state:
    try:
        pr = requests.get(f"{API_BASE}/v2/profile", headers=_headers(), timeout=5)
        st.session_state.profile = pr.json() if pr.status_code == 200 else {}
    except Exception:
        st.session_state.profile = {}

profile = st.session_state.profile
has_psoriasis = profile.get("has_psoriasis", True)
has_psa = profile.get("has_psa", False)
tracks_cycle = profile.get("tracks_cycle", False)


# SIDEBAR
with st.sidebar:
    if st.button("Logout"):
        st.session_state.pop("token", None)
        st.session_state.pop("profile", None)
        st.rerun()

    st.divider()
    with st.expander("Profile Settings"):
        pso_toggle = st.checkbox("I have Psoriasis", value=has_psoriasis)
        psa_toggle = st.checkbox("I have Psoriatic Arthritis (PsA)", value=has_psa)
        cycle_toggle = st.checkbox("Track Menstrual Cycle", value=profile.get("tracks_cycle", False))
        location_city = st.text_input("City (optional)", value=profile.get("location_city") or "")
        timezone = st.text_input("Timezone", value=profile.get("timezone", "UTC"))

        if st.button("Save Profile"):
            patch_payload = {
                "has_psoriasis": pso_toggle,
                "has_psa": psa_toggle,
                "tracks_cycle": cycle_toggle,
                "location_city": location_city or None,
                "timezone": timezone or "UTC",
            }
            pr = requests.patch(
                f"{API_BASE}/v2/profile",
                json=patch_payload,
                headers=_headers(),
                timeout=5,
            )
            if pr.status_code == 200:
                st.session_state.profile = pr.json()
                st.success("Profile saved")
                st.rerun()
            else:
                st.error(pr.json().get("detail", pr.text))


# HEADER
st.title("Psoriasis Personalized Agent")
st.caption("Daily tracking • Weekly insights • ML-powered flare prediction")

st.divider()
view_mode = st.radio(
    "View Mode",
    options=["Weekly", "Monthly"],
    horizontal=True,
)

if view_mode == "Weekly":
    weeks = 1
    days = 7
else:
    weeks = 4
    days = 30

# ADD DAILY ENTRY FORM
st.divider()
st.subheader("Add Daily Entry")

_JOINT_OPTIONS = ["DIP", "PIP", "MCP", "Wrist", "Elbow", "Shoulder", "Hip", "Knee", "Ankle", "Sacroiliac"]
_PLAQUE_OPTIONS = ["Scalp", "Elbows", "Knees", "Lower Back", "Nails", "Face", "Trunk", "Hands/Feet"]

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
        legacy_flare_flag = st.selectbox("Flare Today?", [0, 1])

    notes = st.text_input("Notes")

    # PsA-gated fields
    morning_stiffness_minutes = None
    affected_joints = None
    functional_limitation = None
    if has_psa:
        st.markdown("**Psoriatic Arthritis**")
        psa_c1, psa_c2 = st.columns(2)
        with psa_c1:
            morning_stiffness_minutes = st.slider(
                "Morning Stiffness (minutes)", 0, 480, 0, step=5,
                help="If stiffness exceeded 8 hours, log 480 and note actual duration."
            )
            functional_limitation = st.slider("Functional Limitation (0–10)", 0, 10, 0)
        with psa_c2:
            affected_joints = st.multiselect("Affected Joints", _JOINT_OPTIONS)

    # Psoriasis-gated fields
    bsa_estimate = None
    plaque_locations = None
    if has_psoriasis:
        st.markdown("**Psoriasis**")
        pso_c1, pso_c2 = st.columns(2)
        with pso_c1:
            bsa_estimate = st.slider("BSA Estimate (%)", 0.0, 100.0, 0.0, step=0.5)
        with pso_c2:
            plaque_locations = st.multiselect("Plaque Locations", _PLAQUE_OPTIONS)

    # Lifestyle triggers — always shown
    st.markdown("**Lifestyle**")
    lf_c1, lf_c2 = st.columns(2)
    with lf_c1:
        log_alcohol = st.checkbox("Log alcohol today?")
        alcohol_units = st.number_input("Alcohol units", min_value=0, value=0, step=1) if log_alcohol else None
    with lf_c2:
        illness_active = st.checkbox("Illness active?")
        illness_description = None
        if illness_active:
            illness_description = st.text_input("Illness description (optional, max 500 chars)")

    # Cycle phase — gated by tracks_cycle
    cycle_day_of_period = None
    if tracks_cycle:
        st.markdown("**Cycle**")
        cycle_day_of_period = st.number_input("Day of period", min_value=1, max_value=60, value=1, step=1)

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
        "legacy_flare_flag": legacy_flare_flag,
        "notes": notes,
    }

    if has_psa:
        payload["morning_stiffness_minutes"] = morning_stiffness_minutes
        payload["affected_joints"] = affected_joints or []
        payload["functional_limitation"] = functional_limitation

    if has_psoriasis:
        payload["bsa_estimate"] = bsa_estimate
        payload["plaque_locations"] = plaque_locations or []

    if log_alcohol:
        payload["alcohol_units"] = alcohol_units
    if illness_active:
        payload["illness_active"] = True
        if illness_description:
            payload["illness_description"] = illness_description
    if tracks_cycle and cycle_day_of_period:
        payload["cycle_day_of_period"] = cycle_day_of_period

    res = requests.post(f"{API_BASE}/entries/", json=payload, headers=_headers())
    if _handle_401(res):
        st.stop()
    if res.status_code == 200:
        st.success("Entry saved successfully")
    else:
        st.error(res.text)

# LOAD DATA
entries_res = requests.get(f"{API_BASE}/entries/", headers=_headers())
if _handle_401(entries_res):
    st.stop()
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
st.subheader("Summary")

summary_res = requests.get(
    f"{API_BASE}/entries/summary?weeks={weeks}",
    headers=_headers(),
)
if _handle_401(summary_res):
    st.stop()

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

# WEATHER PANEL — shown only when profile has a saved location
if profile.get("location_lat") and profile.get("location_lon"):
    st.divider()
    st.subheader("Today's Weather")
    today_str = date.today().isoformat()
    try:
        ctx_res = requests.get(f"{API_BASE}/v2/entries/{today_str}/context", headers=_headers(), timeout=5)
        if ctx_res.status_code == 200:
            w = ctx_res.json().get("weather")
            if w:
                wc1, wc2, wc3, wc4, wc5, wc6 = st.columns(6)
                wc1.metric("Temp (°C)",   f"{w['temperature_c']:.1f}"    if w["temperature_c"]    is not None else "—")
                wc2.metric("Humidity (%)", f"{w['humidity_pct']:.1f}"    if w["humidity_pct"]     is not None else "—")
                wc3.metric("UV Index",     f"{w['uv_index']:.1f}"        if w["uv_index"]         is not None else "—")
                wc4.metric("Rain (mm)",    f"{w['precipitation_mm']:.1f}" if w["precipitation_mm"] is not None else "—")
                wc5.metric("Cloud (%)",    f"{w['cloud_cover_pct']:.1f}" if w["cloud_cover_pct"]  is not None else "—")
                wc6.metric("Pressure",     f"{w['pressure_hpa']:.1f}"   if w["pressure_hpa"]     is not None else "—")
            else:
                st.caption("Weather data not yet available for today — will appear after the next page load.")
    except Exception:
        pass

# RISK TREND
st.divider()
st.subheader("Symptom Trend with Risk Bands")

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
st.subheader("Daily Entries")

_BASE_DISPLAY_COLS = [
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
    "legacy_flare_flag",
    "notes",
]

# Add clinical/trigger columns only if data is present in the returned entries
_CLINICAL_COLS = [
    "morning_stiffness_minutes",
    "affected_joints",
    "functional_limitation",
    "bsa_estimate",
    "plaque_locations",
    "alcohol_units",
    "illness_active",
    "illness_description",
    "cycle_day_of_period",
]

display_cols = _BASE_DISPLAY_COLS + [c for c in _CLINICAL_COLS if c in df_view.columns and df_view[c].notna().any()]

st.dataframe(
    df_view[display_cols].sort_values("date", ascending=False),
    use_container_width=True,
)

# ML PREDICTION
st.divider()
st.subheader("Flare Risk Prediction")

pred_res = requests.get(f"{API_BASE}/ml/predict", headers=_headers())
if _handle_401(pred_res):
    st.stop()

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
