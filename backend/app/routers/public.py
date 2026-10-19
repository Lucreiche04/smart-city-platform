"""Endpoints publics (citoyens, élus, dashboard). Lecture seule, sans authentification."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..database import execute, fetch_all, fetch_one
from ..schemas import POLLUTANTS, SensorReading, SubscriberIn
from ..security import audit, require_iot_key
from ..services import mobility, predictor
from ..services.mqtt_ingest import process_reading
from ..services.recommendations import for_pm25
from ..services.report_pdf import weekly_report
from ..services.repository import history, latest_by_station, pollution_weather, thresholds

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/health")
def health():
    fetch_one("SELECT 1")
    return {"status": "ok"}


@router.get("/stations")
def stations():
    return fetch_all("SELECT code, name, zone, lat, lon, kind FROM stations ORDER BY id")


@router.get("/measurements/latest", summary="Dernières valeurs par station (US-004, US-012)")
def latest():
    return latest_by_station()


@router.get("/kpis", summary="KPI du dashboard : moyenne actuelle de chaque polluant")
def kpis():
    rows = fetch_all(
        """SELECT pollutant, round(avg(value)::numeric, 1)::float AS value, max(time) AS updated_at
           FROM measurements WHERE NOT is_anomaly AND time > now() - interval '2 hours'
             AND pollutant IN ('pm25','pm10','no2','o3') GROUP BY pollutant""")
    th = thresholds()
    for r in rows:
        r["threshold"] = th.get(r["pollutant"])
        r["exceeded"] = r["threshold"] is not None and r["value"] > r["threshold"]
    return rows


@router.get("/measurements/history", summary="Évolution horaire d'un polluant (US-005, US-006)")
def measurement_history(pollutant: str = Query("pm25"), hours: int = Query(24, ge=1, le=720)):
    if pollutant not in POLLUTANTS:
        raise HTTPException(422, f"Polluant inconnu. Valeurs possibles : {sorted(POLLUTANTS)}")
    return {"pollutant": pollutant, "threshold": thresholds().get(pollutant), "points": history(pollutant, hours)}


@router.get("/correlation", summary="PM2.5 et météo alignés (US-013)")
def correlation(hours: int = Query(168, ge=24, le=720)):
    return pollution_weather(hours)


@router.get("/forecast", summary="Prévision PM2.5 J+1 avec fiabilité (US-009, US-011)")
def forecast():
    pred = predictor.latest_prediction()
    if pred is None:
        try:
            pred = predictor.predict_tomorrow()
        except Exception as exc:
            raise HTTPException(503, f"Prévision indisponible : {exc}")
    return pred


@router.get("/mobility", summary="Trafic, lien trafic-pollution et conseil citoyen (données de mobilité)")
def mobility_overview(hours: int = Query(48, ge=6, le=720)):
    return mobility.overview(hours)


@router.get("/recommendations", summary="Conseils selon le niveau de pollution (US-016)")
def recommendations():
    row = fetch_one("""SELECT avg(value) AS v FROM measurements WHERE pollutant = 'pm25'
                       AND NOT is_anomaly AND time > now() - interval '2 hours'""")
    if not row or row["v"] is None:
        raise HTTPException(404, "Pas de mesure récente")
    return for_pm25(float(row["v"]))


@router.get("/reports/weekly.pdf", summary="Rapport PDF de la semaine (US-014)")
def report():
    return Response(weekly_report(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=rapport-qualite-air.pdf"})


@router.post("/ingest", summary="Ingestion HTTP d'un capteur (alternative à MQTT)",
             dependencies=[Depends(require_iot_key)])
def ingest(reading: SensorReading):
    return process_reading(reading, source="iot-http")


@router.post("/subscribers", status_code=201, summary="S'abonner aux alertes (consentement explicite)")
def subscribe(body: SubscriberIn, request: Request):
    execute("INSERT INTO subscribers (email) VALUES (:e) ON CONFLICT DO NOTHING", e=body.email.lower())
    audit("public", "subscribe", request)
    return {"status": "abonné"}


@router.delete("/subscribers/{email}", summary="Droit à l'oubli : suppression de l'email")
def unsubscribe(email: str, request: Request):
    execute("DELETE FROM subscribers WHERE email = :e", e=email.lower())
    audit("public", "unsubscribe", request)     # on ne logge PAS l'email lui-même
    return {"status": "données supprimées"}
