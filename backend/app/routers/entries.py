from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas

router = APIRouter(
    prefix="/entries",
    tags=["Entries"]
)


@router.post("/", response_model=schemas.Entry)
def create_or_update_entry(
    entry: schemas.EntryCreate,
    db: Session = Depends(get_db)
):
    return crud.upsert_entry(db, entry)



@router.get("/", response_model=list[schemas.Entry])
def list_entries(db: Session = Depends(get_db)):
    return crud.get_all_entries(db)



@router.get("/summary", response_model=schemas.SummaryResponse)
def get_summary(
    weeks: int = 1,
    db: Session = Depends(get_db)
):
    summary = crud.get_summary_for_weeks(db, weeks)

    if not summary:
        raise HTTPException(
            status_code=404,
            detail="No entries found"
        )

    return summary



@router.get("/trends", response_model=list[schemas.Entry])
def get_trends(
    days: int = 14,
    db: Session = Depends(get_db)
):
    rows = crud.get_recent_entries(db, days)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No recent entries found"
        )

    return rows
