"""Espace administrateur, protégé par JWT (US-008)."""
import os
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..config import settings
from ..database import execute, fetch_all, fetch_one
from ..limiter import limiter
from ..schemas import ThresholdUpdate, Token
from ..security import audit, create_token, get_current_admin, verify_password
from ..services import predictor
from ..services.collectors import collect_hourly

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/auth/login", response_model=Token)
@limiter.limit("5/minute")        # freine les attaques par force brute
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    user = fetch_one("SELECT username, password_hash FROM users WHERE username = :u", u=form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        audit(form.username[:50], "login_failed", request)
        raise HTTPException(401, "Identifiants incorrects")
    audit(user["username"], "login_success", request)
    return {"access_token": create_token(user["username"])}


@router.get("/admin/audit-logs")
def audit_logs(limit: int = 100, admin: str = Depends(get_current_admin)):
    return fetch_all("SELECT * FROM audit_logs ORDER BY time DESC LIMIT :l", l=min(limit, 500))


@router.get("/admin/app-logs", summary="Dernières lignes du log applicatif (US-018)")
def app_logs(lines: int = 200, admin: str = Depends(get_current_admin)):
    path = os.path.join(settings.log_dir, "app.log")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(deque(f, maxlen=min(lines, 1000)))


@router.get("/admin/thresholds")
def get_thresholds(admin: str = Depends(get_current_admin)):
    return fetch_all("SELECT * FROM thresholds ORDER BY pollutant")


@router.put("/admin/thresholds")
def set_threshold(body: ThresholdUpdate, request: Request, admin: str = Depends(get_current_admin)):
    execute("""INSERT INTO thresholds VALUES (:p, :v)
               ON CONFLICT (pollutant) DO UPDATE SET value = EXCLUDED.value""", p=body.pollutant, v=body.value)
    audit(admin, "threshold_update", request, f"{body.pollutant}={body.value}")
    return {"status": "ok"}


@router.get("/admin/alerts")
def list_alerts(admin: str = Depends(get_current_admin)):
    return fetch_all("""SELECT a.*, s.name AS station FROM alerts a LEFT JOIN stations s ON s.id = a.station_id
                        ORDER BY a.time DESC LIMIT 100""")


@router.get("/admin/anomalies")
def anomalies(admin: str = Depends(get_current_admin)):
    return fetch_all("""SELECT m.time, s.code, m.pollutant, m.value, m.anomaly_score
                        FROM measurements m JOIN stations s ON s.id = m.station_id
                        WHERE m.is_anomaly ORDER BY m.time DESC LIMIT 100""")


@router.get("/admin/model")
def model_info(admin: str = Depends(get_current_admin)):
    return predictor.model_meta() or {}


@router.post("/admin/collect-now", summary="Déclenche une collecte immédiate (utile en démo)")
def collect_now(request: Request, admin: str = Depends(get_current_admin)):
    collect_hourly()
    audit(admin, "manual_collect", request)
    return {"status": "collecte lancée"}


@router.post("/admin/predict-now")
def predict_now(request: Request, admin: str = Depends(get_current_admin)):
    audit(admin, "manual_predict", request)
    return predictor.predict_tomorrow()
