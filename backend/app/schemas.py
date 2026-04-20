from pydantic import BaseModel
from typing import Optional
from typing import List

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


