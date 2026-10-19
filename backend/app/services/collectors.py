"""Collecte horaire (US-001) : AQICN pour la pollution, OpenWeatherMap pour la météo.

Points d'attention :
- AQICN renvoie des INDICES AQI (échelle US EPA), pas des µg/m³. On reconvertit
  PM2.5 et PM10 en concentration pour comparer aux seuils du client (en µg/m³).
- Les appels réseau peuvent échouer : on log l'erreur et on réessaie à l'heure
  suivante plutôt que de faire planter l'application.
"""
import logging
from datetime import datetime, timezone

import httpx

from ..config import settings
from ..database import execute
from . import alerts
from .repository import save_measurement

log = logging.getLogger("collector")

# Points de rupture EPA : (AQI bas, AQI haut, concentration basse, concentration haute)
_BREAKPOINTS = {
    "pm25": [(0, 50, 0, 12), (51, 100, 12.1, 35.4), (101, 150, 35.5, 55.4), (151, 200, 55.5, 150.4),
             (201, 300, 150.5, 250.4), (301, 500, 250.5, 500.4)],
    "pm10": [(0, 50, 0, 54), (51, 100, 55, 154), (101, 150, 155, 254), (151, 200, 255, 354),
             (201, 300, 355, 424), (301, 500, 425, 604)],
}


def aqi_to_concentration(pollutant: str, aqi: float) -> float:
    """Interpolation linéaire inverse de la formule EPA."""
    for a_lo, a_hi, c_lo, c_hi in _BREAKPOINTS.get(pollutant, []):
        if a_lo <= aqi <= a_hi:
            return round(c_lo + (aqi - a_lo) * (c_hi - c_lo) / (a_hi - a_lo), 1)
    return float(aqi)  # NO2, O3, SO2 : AQICN les fournit déjà proches de l'échelle µg/m³ locale


def fetch_air_quality() -> dict:
    url = f"https://api.waqi.info/feed/geo:{settings.city_lat};{settings.city_lon}/"
    r = httpx.get(url, params={"token": settings.aqicn_token}, timeout=15)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != "ok":
        raise RuntimeError(f"AQICN: {body.get('data')}")
    iaqi = body["data"].get("iaqi", {})
    return {p: aqi_to_concentration(p, iaqi[p]["v"]) for p in ("pm25", "pm10", "no2", "o3", "so2") if p in iaqi}


def fetch_weather() -> dict:
    r = httpx.get("https://api.openweathermap.org/data/2.5/weather", timeout=15, params={
        "lat": settings.city_lat, "lon": settings.city_lon, "units": "metric", "appid": settings.openweather_api_key})
    r.raise_for_status()
    d = r.json()
    return {"temperature": d["main"]["temp"], "humidity": d["main"]["humidity"],
            "wind_speed": d["wind"]["speed"], "pressure": d["main"]["pressure"]}


def fetch_weather_forecast_tomorrow() -> dict:
    """Moyenne des prévisions 3h de demain (API gratuite 5 jours / 3 heures)."""
    r = httpx.get("https://api.openweathermap.org/data/2.5/forecast", timeout=15, params={
        "lat": settings.city_lat, "lon": settings.city_lon, "units": "metric", "appid": settings.openweather_api_key})
    r.raise_for_status()
    tomorrow = (datetime.now(timezone.utc).date().toordinal() + 1)
    items = [i for i in r.json()["list"]
             if datetime.fromtimestamp(i["dt"], timezone.utc).date().toordinal() == tomorrow]
    if not items:
        return {}
    n = len(items)
    return {"temperature": sum(i["main"]["temp"] for i in items) / n,
            "humidity": sum(i["main"]["humidity"] for i in items) / n,
            "wind_speed": sum(i["wind"]["speed"] for i in items) / n,
            "pressure": sum(i["main"]["pressure"] for i in items) / n}


def collect_hourly() -> None:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        values = fetch_air_quality()
        for pollutant, value in values.items():
            save_measurement(now, "aqicn-paris", pollutant, value, "aqicn")
            alerts.check(pollutant, value, "aqicn-paris")
        log.info("Collecte AQICN OK : %s", values)
    except Exception:
        log.exception("Échec collecte AQICN")
    if settings.openweather_api_key:
        try:
            w = fetch_weather()
            execute("""INSERT INTO weather VALUES (:t, :temperature, :humidity, :wind_speed, :pressure)
                       ON CONFLICT (time) DO NOTHING""", t=now, **w)
            log.info("Collecte météo OK : %s", w)
        except Exception:
            log.exception("Échec collecte OpenWeatherMap")
