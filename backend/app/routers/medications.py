from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app import crud, schemas

router = APIRouter(prefix="/v2/medications", tags=["Medications"])


@router.post("/events", response_model=schemas.MedicationEventRead, status_code=201)
def create_event(
    event: schemas.MedicationEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_medication_event(db, event, current_user.id)


@router.get("/events", response_model=list[schemas.MedicationEventRead])
def list_events(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_medication_events(db, current_user.id, from_date, to_date)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = crud.delete_medication_event(db, event_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Medication event not found")
    return Response(status_code=204)
