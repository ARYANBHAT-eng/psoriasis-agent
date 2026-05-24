from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import Entry
from app.schemas import EntryCreate


def upsert_entry(db: Session, entry: EntryCreate, user_id: int):
    existing = (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.date == entry.date)
        .first()
    )

    # Exclude psoriasis_flare — it is a v1 input compat field, not an ORM column.
    # The model_validator already mapped it to legacy_flare_flag before we get here.
    data = entry.model_dump(exclude={"psoriasis_flare"})

    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        obj = existing
    else:
        obj = Entry(user_id=user_id, **data)
        db.add(obj)

    db.commit()
    db.refresh(obj)
    return obj


def get_all_entries(db: Session, user_id: int):
    return (
        db.query(Entry)
        .filter(Entry.user_id == user_id)
        .order_by(Entry.date.asc())
        .all()
    )


def get_summary_for_weeks(db: Session, user_id: int, weeks: int = 1):
    rows = get_all_entries(db, user_id)

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


def get_recent_entries(db: Session, user_id: int, days: int):
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    return (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.date >= cutoff)
        .order_by(Entry.date.asc())
        .all()
    )
