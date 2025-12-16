
from pydantic import BaseModel
from typing import Optional

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
    psoriasis_flare: int
    notes: Optional[str] = ""

class EntryCreate(EntryBase):
    pass

class Entry(EntryBase):
    id: int
    model_config = {"from_attributes": True}

class SummaryResponse(BaseModel):
    avg_symptom: float
    avg_sleep: float
    missed_med_days: int
    avg_stress: float
    latest_symptom_total: float
