
from sqlalchemy import Column, Integer, Float, String
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
