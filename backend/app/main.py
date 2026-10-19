"""Point d'entrée de l'API.

Au démarrage :
1. configure les logs JSON ;
2. crée le compte admin s'il n'existe pas ;
3. amorce la base avec le CSV historique si elle est vide (critère "7 jours d'historique") ;
4. entraîne un premier modèle s'il n'y en a pas ;
5. lance l'abonné MQTT et les tâches planifiées.
"""
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import fetch_one
from .limiter import limiter
from .logging_conf import setup_logging
from .routers import admin, public
from .security import ensure_admin_user

setup_logging()
log = logging.getLogger("app")


def bootstrap() -> None:
    ensure_admin_user()
    csv_path = os.path.join(settings.data_dir, "historique.csv")           # CSV fourni par le client
    if not os.path.exists(csv_path):
        csv_path = os.path.join(settings.model_dir, "historique_synthetique.csv")  # volume Docker inscriptible
    if fetch_one("SELECT count(*) AS n FROM measurements")["n"] == 0:
        from ml.import_csv import import_csv
        if not os.path.exists(csv_path):
            from ml.synthetic import generate
            log.warning("Aucun CSV fourni : génération de 180 jours synthétiques")
            generate(180).to_csv(csv_path, index=False)
        log.info("Import historique : %s mesures", import_csv(csv_path))
    if not os.path.exists(os.path.join(settings.model_dir, "pm25_model.joblib")):
        from ml.train import train
        meta = train(csv_path, settings.model_dir)
        log.info("Premier modèle entraîné : %s", meta["best_model"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs = []
    if settings.enable_background:
        bootstrap()
        from .services import mqtt_ingest, scheduler
        jobs = [mqtt_ingest.start(), scheduler.start()]
    yield
    for j in jobs:
        (j.loop_stop if hasattr(j, "loop_stop") else j.shutdown)()


app = FastAPI(
    title="Plateforme Smart City — API",
    description="Qualité de l'air et mobilité. Documentation générée automatiquement (Swagger).",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Log de chaque requête avec sa durée (aide au debugging et au suivi du < 3 s)."""
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    if request.url.path != "/metrics":
        log.info("%s %s -> %s en %.0f ms", request.method, request.url.path, response.status_code, ms)
    return response


app.include_router(public.router)
app.include_router(admin.router)
Instrumentator().instrument(app).expose(app, include_in_schema=False)   # /metrics pour Prometheus
