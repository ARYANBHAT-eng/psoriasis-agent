import logging
import zoneinfo
from datetime import datetime, timezone
from typing import Optional

import requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def user_today_str(timezone_str: str) -> str:
    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")
    return datetime.now(tz).strftime("%Y-%m-%d")


def _hourly_noon(hourly: dict, key: str) -> Optional[float]:
    values = hourly.get(key)
    if values and len(values) > 12:
        return values[12]  # index 12 = noon UTC
    return None


def fetch_and_save(user_id: int, lat: float, lon: float, date_str: str, db: Session) -> None:
    """Fetch weather from Open-Meteo and persist. Idempotent — no-ops if record exists."""
    from app.models import WeatherCapture

    if db.query(WeatherCapture).filter(
        WeatherCapture.user_id == user_id, WeatherCapture.date == date_str
    ).first():
        return

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,uv_index_max,precipitation_sum",
                "hourly": "relative_humidity_2m,cloud_cover,pressure_msl",
                "start_date": date_str,
                "end_date": date_str,
                "timezone": "UTC",
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Open-Meteo fetch failed user=%s date=%s: %s", user_id, date_str, exc)
        return

    daily = data.get("daily", {})
    hourly = data.get("hourly", {})
    capture = WeatherCapture(
        user_id=user_id,
        date=date_str,
        temperature_c=(daily.get("temperature_2m_max") or [None])[0],
        uv_index=(daily.get("uv_index_max") or [None])[0],
        precipitation_mm=(daily.get("precipitation_sum") or [None])[0],
        humidity_pct=_hourly_noon(hourly, "relative_humidity_2m"),
        cloud_cover_pct=_hourly_noon(hourly, "cloud_cover"),
        pressure_hpa=_hourly_noon(hourly, "pressure_msl"),
        source="open-meteo",
    )
    try:
        db.add(capture)
        db.commit()
    except Exception:
        db.rollback()  # unique constraint race — another concurrent task won


def run_weather_task(user_id: int, lat: float, lon: float, date_str: str) -> None:
    """BackgroundTask entry point — creates its own DB session."""
    import app.database as _database

    db = _database.SessionLocal()
    try:
        fetch_and_save(user_id, lat, lon, date_str, db)
    except Exception as exc:
        logger.warning("Weather background task failed user=%s: %s", user_id, exc)
    finally:
        db.close()


def maybe_trigger_weather(bg, user, db: Session) -> None:
    """Add run_weather_task to BackgroundTasks if user has location and no capture today."""
    from app.models import UserProfile, WeatherCapture

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile or not profile.location_lat or not profile.location_lon:
        return

    today = user_today_str(profile.timezone or "UTC")
    if db.query(WeatherCapture).filter(
        WeatherCapture.user_id == user.id, WeatherCapture.date == today
    ).first():
        return

    bg.add_task(run_weather_task, user.id, profile.location_lat, profile.location_lon, today)
