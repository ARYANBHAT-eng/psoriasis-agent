import os
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

FEATURE_ORDER = [
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
]

class MLModel:
    def __init__(self):
        self.pipeline = None

    def model_exists(self):
        return os.path.exists(MODEL_PATH)

    def load(self):
        if self.model_exists():
            self.pipeline = joblib.load(MODEL_PATH)
            return True
        return False

    def save(self):
        if self.pipeline is None:
            raise RuntimeError("No trained model to save")
        joblib.dump(self.pipeline, MODEL_PATH)

    def _clean_rows(self, rows_dict):
        clean = []
        for r in rows_dict:
            r = dict(r)
            r.pop("_sa_instance_state", None)
            clean.append(r)
        return clean

    def train_and_save(self, rows_dict):
        rows_dict = self._clean_rows(rows_dict)
        df = pd.DataFrame(rows_dict)

        for f in FEATURE_ORDER + ["psoriasis_flare"]:
            if f not in df.columns:
                df[f] = 0

        if df["psoriasis_flare"].isnull().all():
            raise ValueError("psoriasis_flare label (0/1) required for training")

        df = df.dropna()

        X = df[FEATURE_ORDER].astype(float).values
        y = df["psoriasis_flare"].astype(int).values

        if len(X) < 10:
            raise ValueError("At least 10 entries required to train model")

        self.pipeline = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000))
        ])

        self.pipeline.fit(X, y)
        self.save()

        return {
            "status": "trained",
            "samples": int(len(X))
        }

    def predict_next(self, rows_dict):
        rows_dict = self._clean_rows(rows_dict)

        if not self.pipeline and not self.load():
            raise RuntimeError("Model not trained yet")

        if not rows_dict:
            raise ValueError("No data available for prediction")

        df = pd.DataFrame(rows_dict)

        for f in FEATURE_ORDER:
            if f not in df.columns:
                df[f] = 0

        last = df.iloc[-1]
        X = last[FEATURE_ORDER].astype(float).values.reshape(1, -1)

        prob = float(self.pipeline.predict_proba(X)[0][1])
        risk = risk_level_from_prob(prob)

        model_factors = explain_by_model(self.pipeline, last)
        rule_factors = explain_by_rules(last)
        
        recommendations = generate_recommendations(risk, last.to_dict())
        return {
            "probability_of_flare": prob,
            "risk_level": risk,
            "key_factors": model_factors + rule_factors,
            "recommendations": recommendations
        }


def risk_level_from_prob(prob: float) -> str:
    if prob < 0.4:
        return "LOW"
    elif prob <= 0.7:
        return "MEDIUM"
    return "HIGH"


def explain_by_model(pipeline, last_row: pd.Series):
    clf = pipeline.named_steps["clf"]
    coefs = clf.coef_[0]

    impacts = list(zip(FEATURE_ORDER, coefs))
    impacts.sort(key=lambda x: abs(x[1]), reverse=True)

    explanations = []
    for feature, weight in impacts[:3]:
        value = last_row.get(feature, 0)
        if value > 0:
            direction = "increases" if weight > 0 else "reduces"
            explanations.append(
                f"{feature.replace('_', ' ').title()} {direction} flare risk"
            )

    return explanations


def explain_by_rules(last_row: pd.Series):
    rules = []

    if last_row.get("stress_level", 0) >= 7:
        rules.append("High stress level detected")

    if last_row.get("sleep_quality", 10) <= 4:
        rules.append("Poor sleep quality")

    if last_row.get("missed_medication", 0) == 1:
        rules.append("Recent missed medication")

    if last_row.get("joint_pain", 0) >= 5:
        rules.append("Increased joint pain")

    if not rules:
        rules.append("Current symptoms appear stable")

    return rules


model = MLModel()

def train_and_save(rows_dict):
    return model.train_and_save(rows_dict)

def predict_next(rows_dict):
    return model.predict_next(rows_dict)
def generate_recommendations(risk_level: str, last_row: dict):
    recs = []

    if risk_level == "HIGH":
        recs.append("Consider consulting your dermatologist")
        recs.append("Avoid known personal triggers if possible")

    if last_row.get("stress_level", 0) >= 7:
        recs.append("Practice stress reduction (breathing, light exercise)")

    if last_row.get("sleep_quality", 10) <= 4:
        recs.append("Improve sleep routine (consistent timing, less screen time)")

    if last_row.get("missed_medication", 0) == 1:
        recs.append("Ensure medication adherence")

    if last_row.get("joint_pain", 0) >= 5:
        recs.append("Avoid high-impact physical strain")

    if not recs:
        recs.append("Maintain current routine")

    return recs

