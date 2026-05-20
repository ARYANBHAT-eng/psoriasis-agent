
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, LargeBinary, String, Text
from app.database import Base

class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)
    itch = Column(Float, nullable=False)
    redness = Column(Float, nullable=False)
    scaling = Column(Float, nullable=False)
    joint_pain = Column(Float, nullable=False)
    fatigue = Column(Float, nullable=False)
    stress_level = Column(Float, nullable=False)
    sleep_quality = Column(Float, nullable=False)
    diet_quality = Column(Float, nullable=False)
    missed_medication = Column(Integer, nullable=False)   # 0 / 1
    topical_applied = Column(Integer, nullable=False)     # 0 / 1
    psoriasis_flare = Column(Integer, nullable=False)     # 0 / 1 (LABEL)
    notes = Column(String, default="")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, nullable=False, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    event_type = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    success = Column(Boolean, nullable=False)
    details_json = Column(Text, nullable=True)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    # metrics_json schema: {"sample_count": int, "accuracy": float,
    #                        "features": list[str], "classes": list[int],
    #                        "trained_at": "ISO 8601 string"}
    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), nullable=False, index=True,
                        default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    artifact_bytes = Column(LargeBinary, nullable=False)
    metrics_json = Column(Text, nullable=True)
