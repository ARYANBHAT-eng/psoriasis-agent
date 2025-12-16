from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import DailyEntry
from app.schemas import EntryCreate


def upsert_entry(db: Session, entry: EntryCreate):
    existing = (
        db.query(DailyEntry)
        .filter(DailyEntry.date == entry.date)
        .first()
    )

    if existing:
        for key, value in entry.model_dump().items():
            setattr(existing, key, value)
        obj = existing
    else:
        obj = DailyEntry(**entry.model_dump())
        db.add(obj)

    db.commit()
    db.refresh(obj)
    return obj

def get_all_entries(db: Session):
    return (
        db.query(DailyEntry)
        .order_by(DailyEntry.date.asc())
        .all()
    )

def get_summary_for_weeks(db: Session, weeks: int = 1):
    rows = get_all_entries(db)

    if not rows:
        return None

    data = rows[-(weeks * 7):]

    symptom_totals = [
        r.itch + r.redness + r.scaling + r.joint_pain + r.fatigue
        for r in data
    ]

    return {
        "avg_symptom": round(sum(symptom_totals) / len(symptom_totals), 2),
        "avg_sleep": round(sum(r.sleep_quality for r in data) / len(data), 2),
        "missed_med_days": sum(r.missed_medication for r in data),
        "avg_stress": round(sum(r.stress_level for r in data) / len(data), 2),
        "latest_symptom_total": round(symptom_totals[-1], 2),
    }

def get_recent_entries(db: Session, days: int):
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    return (
        db.query(DailyEntry)
        .filter(DailyEntry.date >= cutoff)
        .order_by(DailyEntry.date.asc())
        .all()
    )
