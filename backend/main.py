import logging
import time
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app import models as _models
from app.config import get_settings
from app.routers.entries import router as entries_router
from app.routers.ml import router as ml_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("psoriasis-api")
settings = get_settings()

app = FastAPI(title="Psoriasis Agent API")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Startup config | env=%s", settings.app_env)
    logger.info("Startup config | port=%s", settings.port)
    logger.info("Startup config | db_url_configured=%s", settings.db_url_configured)
    logger.info("Startup config | allowed_origins=%s", settings.allowed_origins)


def get_allowed_origins() -> list[str]:
    return settings.allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(entries_router)
app.include_router(ml_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path == "/healthz":
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "HTTP %s %s -> %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
