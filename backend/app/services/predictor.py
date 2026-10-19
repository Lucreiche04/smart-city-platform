"""Prévision PM2.5 de J+1 (US-009) et niveau de fiabilité (US-011).

Fiabilité affichée à l'utilisateur = 2 informations :
- la précision du modèle mesurée sur les 30 jours de test (100 - MAPE) ;
- un intervalle de confiance à ~95 % : prédiction ± 1,96 × écart-type des erreurs de test.
"""
import json
import logging
import os
from datetime import date, timedelta

import joblib

from ml.features import latest_row, to_daily

from ..config import settings
from ..database import execute, fetch_one
from .collectors import fetch_weather_forecast_tomorrow
from .mobility import tomorrow_traffic
from .recommendations import for_pm25
from .repository import hourly_history

log = logging.getLogger("predictor")
MODEL_PATH = os.path.join(settings.model_dir, "pm25_model.joblib")
META_PATH = os.path.join(settings.model_dir, "metrics.json")


def model_meta() -> dict | None:
    if not os.path.exists(META_PATH):
        return None
    with open(META_PATH) as f:
        return json.load(f)


def predict_tomorrow() -> dict:
    meta = model_meta()
    if meta is None:
        raise RuntimeError("Aucun modèle entraîné : lancer `python -m ml.train`")
    model = joblib.load(MODEL_PATH)
    daily = to_daily(hourly_history(days=30))
    forecast = {}
    if settings.openweather_api_key:
        try:
            forecast = fetch_weather_forecast_tomorrow()
        except Exception:
            log.exception("Prévision météo indisponible, on reprend la météo du jour")
    forecast["traffic_index"] = tomorrow_traffic()
    value = max(float(model.predict(latest_row(daily, forecast, meta.get("features")))[0]), 0)
    margin = 1.96 * meta["residual_std"]
    target = date.today() + timedelta(days=1)
    reliability = meta["metrics"][meta["best_model"]]["precision"]
    execute(
        """INSERT INTO predictions (target_date, value, lower_bound, upper_bound, model, reliability)
           VALUES (:d, :v, :lo, :hi, :m, :r)""",
        d=target, v=value, lo=max(value - margin, 0), hi=value + margin, m=meta["best_model"], r=reliability,
    )
    return latest_prediction()


def latest_prediction() -> dict | None:
    row = fetch_one("SELECT * FROM predictions ORDER BY created_at DESC LIMIT 1")
    if not row:
        return None
    meta = model_meta() or {}
    row["recommendation"] = for_pm25(row["value"])
    row["explanation"] = {
        "model": row["model"],
        "test_days": meta.get("test_days"),
        "metrics": meta.get("metrics", {}).get(row["model"]),
        "baseline": meta.get("metrics", {}).get("baseline_persistence"),
        "top_features": list((meta.get("feature_importances") or {}).items())[:5],
    }
    return row
