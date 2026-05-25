
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, LargeBinary, String, Text, UniqueConstraint,
)
from app.database import Base


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_entries_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(String, index=True, nullable=False)
    itch = Column(Float, nullable=False)
    redness = Column(Float, nullable=False)
    scaling = Column(Float, nullable=False)
    joint_pain = Column(Float, nullable=False)
    fatigue = Column(Float, nullable=False)
    stress_level = Column(Float, nullable=False)
    sleep_quality = Column(Float, nullable=False)
    diet_quality = Column(Float, nullable=False)
    missed_medication = Column(Integer, nullable=False)
    topical_applied = Column(Integer, nullable=False)
    legacy_flare_flag = Column(Integer, nullable=True)
    notes = Column(String, default="")
    morning_stiffness_minutes = Column(Integer, nullable=True)   # 0–480 minutes
    affected_joints = Column(JSON, nullable=True)
    functional_limitation = Column(Integer, nullable=True)       # 0–10
    bsa_estimate = Column(Float, nullable=True)                  # 0.0–100.0 %
    plaque_locations = Column(JSON, nullable=True)
    alcohol_units = Column(Integer, nullable=True)               # 0="none today", NULL="not recorded"
    illness_active = Column(Boolean, nullable=True)
    illness_description = Column(String, nullable=True)
    cycle_day_of_period = Column(Integer, nullable=True)         # gated by tracks_cycle


class WeatherCapture(Base):
    __tablename__ = "weather_captures"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_weather_user_date"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date             = Column(String, nullable=False)
    fetched_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    temperature_c    = Column(Float, nullable=True)
    humidity_pct     = Column(Float, nullable=True)
    uv_index         = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    cloud_cover_pct  = Column(Float, nullable=True)
    pressure_hpa     = Column(Float, nullable=True)
    source           = Column(String, nullable=False, default="open-meteo")


class MedicationEvent(Base):
    __tablename__ = "medication_events"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date            = Column(String, nullable=False, index=True)
    recorded_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    medication_name = Column(String, nullable=False)
    event_type      = Column(String, nullable=False)   # validated as enum in schema
    dose            = Column(String, nullable=True)
    notes           = Column(String, nullable=True)


class FlareEvent(Base):
    __tablename__ = "flare_events"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date        = Column(String, nullable=False, index=True)
    end_date          = Column(String, nullable=True)              # NULL = open/ongoing
    condition_type    = Column(String, nullable=False)             # "psoriasis" | "psa" | "both"
    severity          = Column(Integer, nullable=True)             # 1–10; NULL on legacy backfills
    confidence_source = Column(String, nullable=False)             # "user_confirmed" | "algorithm_derived" | "legacy"
    notes             = Column(String, nullable=True)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    has_psoriasis = Column(Boolean, nullable=False, default=True)
    has_psa = Column(Boolean, nullable=False, default=False)
    tracks_cycle = Column(Boolean, nullable=False, default=False)
    location_city = Column(String, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
