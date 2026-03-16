import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers.entries import router as entries_router
from app.routers.ml import router as ml_router

# Optional: helps prevent heavy ML thread spawning on small servers
os.environ["OMP_NUM_THREADS"] = "1"

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Psoriasis Agent API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(entries_router)
app.include_router(ml_router)

# Health check endpoint (important for Render)
@app.get("/")
def health():
    return {"status": "Psoriasis Agent API running"}