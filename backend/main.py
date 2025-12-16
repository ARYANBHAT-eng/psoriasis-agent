
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers.entries import router as entries_router
from app.routers.ml import router as ml_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Psoriasis Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entries_router)
app.include_router(ml_router)
