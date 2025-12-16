
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/entries", tags=["Entries"])

@router.post("/", response_model=schemas.Entry)
def create_entry(entry: schemas.EntryCreate, db: Session = Depends(get_db)):
    return crud.upsert_entry(db, entry)

@router.get("/")
def list_entries(db: Session = Depends(get_db)):
    return crud.get_all_entries(db)
