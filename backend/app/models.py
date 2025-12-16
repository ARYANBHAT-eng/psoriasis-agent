
from sqlalchemy import Column, Integer, Float, String
from app.database import Base

class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    itch = Column(Float)
    redness = Column(Float)
    scaling = Column(Float)
    joint_pain = Column(Float)
    fatigue = Column(Float)
    stress_level = Column(Float)
    sleep_quality = Column(Float)
    diet_quality = Column(Float)
    missed_medication = Column(Integer)
    topical_applied = Column(Integer)
    psoriasis_flare = Column(Integer)
    notes = Column(String)
