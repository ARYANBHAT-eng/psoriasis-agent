import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import check_db_connection, SessionLocal
from app.config import get_settings
from app.ml_model import maybe_auto_train
from app.routers.auth import router as auth_router
from app.routers.entries import router as entries_router
from app.routers.ml import router as ml_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("psoriasis-api")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup config | env=%s", settings.app_env)
    logger.info("Startup config | port=%s", settings.port)
    logger.info("Startup config | database_url=%s", settings.database_url)
    logger.info("Startup config | allowed_origins=%s", settings.allowed_origins)
    with SessionLocal() as db:
        maybe_auto_train(db)
    yield


app = FastAPI(title="Psoriasis Agent API", lifespan=lifespan)


def get_allowed_origins() -> list[str]:
    return settings.get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(auth_router)
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
    if check_db_connection():
        return {"status": "ok", "database": "connected"}
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "database": "unreachable"},
    )
