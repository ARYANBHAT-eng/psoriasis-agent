from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import Entry, FlareEvent, MedicationEvent
from app.schemas import EntryCreate, FlareEventCreate, FlareEventUpdate, MedicationEventCreate


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


def get_entry_by_date(db: Session, user_id: int, date: str):
    return db.query(Entry).filter(Entry.user_id == user_id, Entry.date == date).first()


def get_recent_entries(db: Session, user_id: int, days: int):
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    return (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.date >= cutoff)
        .order_by(Entry.date.asc())
        .all()
    )


def create_medication_event(db: Session, event: MedicationEventCreate, user_id: int):
    obj = MedicationEvent(user_id=user_id, **event.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_medication_events(db: Session, user_id: int, from_date=None, to_date=None):
    q = db.query(MedicationEvent).filter(MedicationEvent.user_id == user_id)
    if from_date:
        q = q.filter(MedicationEvent.date >= from_date)
    if to_date:
        q = q.filter(MedicationEvent.date <= to_date)
    return q.order_by(MedicationEvent.date.desc()).all()


def delete_medication_event(db: Session, event_id: int, user_id: int) -> bool:
    obj = db.query(MedicationEvent).filter(
        MedicationEvent.id == event_id,
        MedicationEvent.user_id == user_id,
    ).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def create_flare_event(db: Session, event: FlareEventCreate, user_id: int):
    obj = FlareEvent(
        user_id=user_id,
        confidence_source="user_confirmed",
        **event.model_dump(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_flare_events(db: Session, user_id: int, from_date=None, to_date=None, condition=None):
    q = db.query(FlareEvent).filter(FlareEvent.user_id == user_id)
    if from_date:
        q = q.filter(FlareEvent.start_date >= from_date)
    if to_date:
        q = q.filter(FlareEvent.start_date <= to_date)
    if condition:
        q = q.filter(FlareEvent.condition_type == condition)
    return q.order_by(FlareEvent.start_date.desc()).all()


def update_flare_event(db: Session, flare_id: int, user_id: int, update: FlareEventUpdate):
    obj = db.query(FlareEvent).filter(
        FlareEvent.id == flare_id,
        FlareEvent.user_id == user_id,
    ).first()
    if not obj:
        return None
    for k, v in update.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_flare_event(db: Session, flare_id: int, user_id: int) -> bool:
    obj = db.query(FlareEvent).filter(
        FlareEvent.id == flare_id,
        FlareEvent.user_id == user_id,
    ).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
