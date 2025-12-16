from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.ml_model import train_and_save, predict_next

router = APIRouter(prefix="/ml", tags=["ML"])

@router.post("/train")
def train_model(db: Session = Depends(get_db)):
    entries = crud.get_all_entries(db)

    if not entries:
        raise HTTPException(status_code=400, detail="No entries found to train model")

    try:
        return train_and_save([e.__dict__ for e in entries])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/predict")
def predict_flare(db: Session = Depends(get_db)):
    entries = crud.get_all_entries(db)

    if not entries:
        raise HTTPException(status_code=400, detail="No entries found for prediction")

    try:
        return predict_next([e.__dict__ for e in entries])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
