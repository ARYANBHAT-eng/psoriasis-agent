from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

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
    missed_medication: int      # 0 / 1
    topical_applied: int        # 0 / 1
    psoriasis_flare: int        # 0 / 1
    notes: Optional[str] = ""

class EntryCreate(EntryBase):
    pass

class Entry(EntryBase):
    id: int

    model_config = {
        "from_attributes": True  # Pydantic v2 correct replacement
    }

class SummaryResponse(BaseModel):
    avg_symptom: float
    avg_sleep: float
    missed_med_days: int
    avg_stress: float
    latest_symptom_total: float

class TrendResponse(BaseModel):
    days: int
    avg_symptom_start: float
    avg_symptom_end: float
    avg_stress: float
    avg_sleep: float
    flare_days: int
    trend: str

class PredictionResponse(BaseModel):
    probability_of_flare: float
    risk_level: str
    key_factors: List[str]
    recommendations: List[str]


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


