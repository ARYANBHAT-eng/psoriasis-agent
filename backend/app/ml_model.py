import io
import json
import logging
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
        self._trained_at = None

    def load_from_db(self, db: Session) -> bool:
        from app.models import ModelArtifact
        row = (
            db.query(ModelArtifact)
            .filter(ModelArtifact.is_active.is_(True))
            .order_by(ModelArtifact.trained_at.desc())
            .first()
        )
        if row is None:
            return False
        self.pipeline = joblib.load(io.BytesIO(row.artifact_bytes))
        self._trained_at = row.trained_at
        return True

    def _clean_rows(self, rows_dict):
        clean = []
        for r in rows_dict:
            r = dict(r)
            r.pop("_sa_instance_state", None)
            r["missed_medication"] = r["missed_medication"] if r["missed_medication"] is not None else 0
            r["topical_applied"] = r["topical_applied"] if r["topical_applied"] is not None else 0
            clean.append(r)
        return clean

    def train_and_save(self, rows_dict, db: Session):
        rows_dict = self._clean_rows(rows_dict)
        df = pd.DataFrame(rows_dict)

        for f in FEATURE_ORDER + ["legacy_flare_flag"]:
            if f not in df.columns:
                df[f] = 0

        if df["legacy_flare_flag"].isnull().all():
            raise ValueError("legacy_flare_flag label (0/1) required for training")

        training_cols = FEATURE_ORDER + ["legacy_flare_flag"]
        df = df.dropna(subset=training_cols)

        X = df[FEATURE_ORDER].astype(float).values
        y = df["legacy_flare_flag"].astype(int).values

        if len(X) < 10:
            raise ValueError("At least 10 entries required to train model")

        self.pipeline = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ])
        self.pipeline.fit(X, y)

        buf = io.BytesIO()
        joblib.dump(self.pipeline, buf)
        artifact_bytes = buf.getvalue()

        accuracy = float(self.pipeline.score(X, y))
        metrics = {
            "sample_count": int(len(X)),
            "accuracy": accuracy,
            "features": FEATURE_ORDER,
            "classes": list(map(int, self.pipeline.named_steps["clf"].classes_)),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }

        from app.models import ModelArtifact
        db.query(ModelArtifact).update({"is_active": False})
        artifact = ModelArtifact(
            is_active=True,
            artifact_bytes=artifact_bytes,
            metrics_json=json.dumps(metrics),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        self._trained_at = artifact.trained_at
        return {
            "status": "trained",
            "samples": int(len(X)),
            "accuracy": accuracy,
            "model_trained_at": artifact.trained_at.isoformat(),
        }

    def predict_next(self, rows_dict, db: Session):
        if not self.pipeline and not self.load_from_db(db):
            raise ValueError("Model not trained yet")

        rows_dict = self._clean_rows(rows_dict)

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
            "recommendations": recommendations,
            "model_trained_at": self._trained_at.isoformat() if self._trained_at else None,
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


model = MLModel()


def train_and_save(rows_dict, db: Session):
    return model.train_and_save(rows_dict, db)


def predict_next(rows_dict, db: Session):
    return model.predict_next(rows_dict, db)


def maybe_auto_train(db: Session) -> None:
    try:
        from app.models import Entry, ModelArtifact
        if db.query(ModelArtifact).filter(ModelArtifact.is_active.is_(True)).first():
            logger.info("Active model artifact found in DB, skipping auto-train")
            return
        count = db.query(Entry).count()
        if count < 10:
            logger.info("Only %d entries — need 10 to auto-train, skipping", count)
            return
        entries = db.query(Entry).all()
        train_and_save([e.__dict__ for e in entries], db)
        logger.info("Auto-trained model at startup (%d entries)", count)
    except Exception as exc:
        logger.error("maybe_auto_train failed: %s", exc)
