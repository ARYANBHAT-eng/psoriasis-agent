import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_client_ip, get_current_user, log_audit_event
from app.database import get_db
from app.models import Entry, MedicationEvent, User
from app import crud, schemas
from app.services.weather import maybe_trigger_weather

router = APIRouter(prefix="/entries", tags=["Entries"])
v2_router = APIRouter(prefix="/v2/entries", tags=["Entries v2"])


def _gate_cycle(entry: schemas.EntryCreate, current_user: User, db: Session) -> schemas.EntryCreate:
    """Drop cycle_day_of_period if the user's profile has tracks_cycle=False."""
    from app.models import UserProfile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile or not profile.tracks_cycle:
        entry = entry.model_copy(update={"cycle_day_of_period": None})
    return entry


# ---------------------------------------------------------------------------
# v1 routes — preserved for backward compatibility
# ---------------------------------------------------------------------------

@router.post("/", response_model=schemas.Entry)
def create_or_update_entry(
    entry: schemas.EntryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _gate_cycle(entry, current_user, db)
    maybe_trigger_weather(background_tasks, current_user, db)
    return crud.upsert_entry(db, entry, current_user.id)


@router.get("/", response_model=list[schemas.Entry])
def list_entries(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    maybe_trigger_weather(background_tasks, current_user, db)
    return crud.get_all_entries(db, current_user.id)


@router.get("/summary", response_model=schemas.SummaryResponse)
def get_summary(
    weeks: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = crud.get_summary_for_weeks(db, current_user.id, weeks)

    if not summary:
        raise HTTPException(status_code=404, detail="No entries found")

    return summary


@router.get("/trends", response_model=list[schemas.Entry])
def get_trends(
    days: int = 14,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = crud.get_recent_entries(db, current_user.id, days)

    if not rows:
        raise HTTPException(status_code=404, detail="No recent entries found")

    return rows


@router.get("/export")
def export_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Entry).filter(Entry.user_id == current_user.id).all()
    entries = []
    for row in rows:
        d = row.__dict__.copy()
        d.pop("_sa_instance_state", None)
        entries.append(d)

    med_rows = (
        db.query(MedicationEvent)
        .filter(MedicationEvent.user_id == current_user.id)
        .order_by(MedicationEvent.date.asc())
        .all()
    )
    med_events = []
    for row in med_rows:
        d = row.__dict__.copy()
        d.pop("_sa_instance_state", None)
        med_events.append(d)

    data = {
        "user": {
            "username": current_user.username,
            "created_at": str(current_user.created_at),
        },
        "entries": entries,
        "medication_events": med_events,
    }

    log_audit_event("data.export", current_user.username, get_client_ip(request), True)
    return Response(
        content=json.dumps(data, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=my-psoriasis-data.json"},
    )


# ---------------------------------------------------------------------------
# v2 routes — canonical, accepts new clinical fields
# ---------------------------------------------------------------------------

@v2_router.get("/{date}/context", response_model=schemas.EntryContextResponse)
def get_entry_context(
    date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import WeatherCapture
    entry = crud.get_entry_by_date(db, current_user.id, date)
    weather = db.query(WeatherCapture).filter(
        WeatherCapture.user_id == current_user.id,
        WeatherCapture.date == date,
    ).first()
    return schemas.EntryContextResponse(entry=entry, weather=weather)


@v2_router.post("/", response_model=schemas.Entry)
def create_or_update_entry_v2(
    entry: schemas.EntryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _gate_cycle(entry, current_user, db)
    maybe_trigger_weather(background_tasks, current_user, db)
    return crud.upsert_entry(db, entry, current_user.id)


@v2_router.get("/", response_model=list[schemas.Entry])
def list_entries_v2(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    maybe_trigger_weather(background_tasks, current_user, db)
    return crud.get_all_entries(db, current_user.id)
