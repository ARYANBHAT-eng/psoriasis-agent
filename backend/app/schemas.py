from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator


class EntryBase(BaseModel):
    date: str
    itch: float
    redness: float
    scaling: float
    joint_pain: float
    fatigue: float
    stress_level: float
    sleep_quality: float
    diet_quality: float
    missed_medication: int
    topical_applied: int
    # v1 input compat: psoriasis_flare is accepted and mapped to legacy_flare_flag.
    # v1 output (Entry response) returns legacy_flare_flag only — the Streamlit
    # frontend is updated in the same task to read the new field name.
    psoriasis_flare: Optional[int] = None
    legacy_flare_flag: Optional[int] = None
    notes: Optional[str] = ""
    morning_stiffness_minutes: Optional[int] = None
    affected_joints: Optional[List[str]] = None
    functional_limitation: Optional[int] = None
    bsa_estimate: Optional[float] = None
    plaque_locations: Optional[List[str]] = None
    alcohol_units: Optional[int] = None
    illness_active: Optional[bool] = None
    illness_description: Optional[str] = None
    cycle_day_of_period: Optional[int] = None

    @model_validator(mode="after")
    def map_legacy_flare(self):
        if self.legacy_flare_flag is None and self.psoriasis_flare is not None:
            self.legacy_flare_flag = self.psoriasis_flare
        return self

    @field_validator("morning_stiffness_minutes", mode="after")
    @classmethod
    def validate_morning_stiffness(cls, v):
        if v is not None and (v < 0 or v > 480):
            raise ValueError(
                "morning_stiffness_minutes must be 0–480; if stiffness exceeded "
                "8 hours, log 480 and note the actual duration in the notes field"
            )
        return v

    @field_validator("functional_limitation", mode="after")
    @classmethod
    def validate_functional_limitation(cls, v):
        if v is not None and not (0 <= v <= 10):
            raise ValueError("functional_limitation must be between 0 and 10")
        return v

    @field_validator("bsa_estimate", mode="after")
    @classmethod
    def validate_bsa(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("bsa_estimate must be between 0.0 and 100.0")
        return v

    @field_validator("alcohol_units", mode="after")
    @classmethod
    def validate_alcohol(cls, v):
        if v is not None and v < 0:
            raise ValueError("alcohol_units must be 0 or greater")
        return v

    @field_validator("illness_description", mode="after")
    @classmethod
    def validate_illness_description(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError("illness_description must be 500 characters or fewer")
        return v

    @field_validator("cycle_day_of_period", mode="after")
    @classmethod
    def validate_cycle_day(cls, v):
        if v is not None and not (1 <= v <= 60):
            raise ValueError("cycle_day_of_period must be between 1 and 60")
        return v


class EntryCreate(EntryBase):
    pass


class Entry(BaseModel):
    id: int
    date: str
    itch: float
    redness: float
    scaling: float
    joint_pain: float
    fatigue: float
    stress_level: float
    sleep_quality: float
    diet_quality: float
    missed_medication: int
    topical_applied: int
    legacy_flare_flag: Optional[int] = None
    notes: Optional[str] = ""
    morning_stiffness_minutes: Optional[int] = None
    affected_joints: Optional[List[str]] = None
    functional_limitation: Optional[int] = None
    bsa_estimate: Optional[float] = None
    plaque_locations: Optional[List[str]] = None
    alcohol_units: Optional[int] = None
    illness_active: Optional[bool] = None
    illness_description: Optional[str] = None
    cycle_day_of_period: Optional[int] = None

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    avg_symptom: float
    avg_sleep: float
    missed_med_days: int
    avg_stress: float
    latest_symptom_total: float


class PredictionResponse(BaseModel):
    probability_of_flare: float
    risk_level: str
    key_factors: List[str]
    recommendations: List[str]
    model_trained_at: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("password", mode="after")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountDeleteRequest(BaseModel):
    password: str


class UserProfileCreate(BaseModel):
    has_psoriasis: bool = True
    has_psa: bool = False
    tracks_cycle: bool = False
    location_city: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    timezone: str = "UTC"

    @field_validator("location_lat", mode="after")
    @classmethod
    def validate_lat(cls, v):
        if v is not None:
            if not -90 <= v <= 90:
                raise ValueError("location_lat must be between -90 and 90")
            return round(v, 2)
        return v

    @field_validator("location_lon", mode="after")
    @classmethod
    def validate_lon(cls, v):
        if v is not None:
            if not -180 <= v <= 180:
                raise ValueError("location_lon must be between -180 and 180")
            return round(v, 2)
        return v


class UserProfileUpdate(BaseModel):
    has_psoriasis: Optional[bool] = None
    has_psa: Optional[bool] = None
    tracks_cycle: Optional[bool] = None
    location_city: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    timezone: Optional[str] = None

    @field_validator("location_lat", mode="after")
    @classmethod
    def validate_lat(cls, v):
        if v is not None:
            if not -90 <= v <= 90:
                raise ValueError("location_lat must be between -90 and 90")
            return round(v, 2)
        return v

    @field_validator("location_lon", mode="after")
    @classmethod
    def validate_lon(cls, v):
        if v is not None:
            if not -180 <= v <= 180:
                raise ValueError("location_lon must be between -180 and 180")
            return round(v, 2)
        return v


class UserProfileRead(BaseModel):
    id: int
    user_id: int
    has_psoriasis: bool
    has_psa: bool
    tracks_cycle: bool
    location_city: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WeatherCaptureRead(BaseModel):
    id: int
    user_id: int
    date: str
    fetched_at: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    uv_index: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    source: str

    model_config = {"from_attributes": True}


class EntryContextResponse(BaseModel):
    entry: Optional[Entry] = None
    weather: Optional[WeatherCaptureRead] = None
