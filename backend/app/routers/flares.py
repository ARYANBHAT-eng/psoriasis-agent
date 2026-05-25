from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app import crud, schemas

router = APIRouter(prefix="/v2/flares", tags=["Flares"])


@router.post("/", response_model=schemas.FlareEventRead, status_code=201)
def create_flare(
    event: schemas.FlareEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_flare_event(db, event, current_user.id)


@router.get("/", response_model=list[schemas.FlareEventRead])
def list_flares(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date:   Optional[str] = Query(None, alias="to"),
    condition: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_flare_events(db, current_user.id, from_date, to_date, condition)


@router.patch("/{flare_id}", response_model=schemas.FlareEventRead)
def update_flare(
    flare_id: int,
    update: schemas.FlareEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = crud.update_flare_event(db, flare_id, current_user.id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Flare event not found")
    return result


@router.delete("/{flare_id}", status_code=204)
def delete_flare(
    flare_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not crud.delete_flare_event(db, flare_id, current_user.id):
        raise HTTPException(status_code=404, detail="Flare event not found")
    return Response(status_code=204)
