"""Tâches planifiées. APScheduler tourne dans le processus du backend :
pas besoin d'un cron système ni d'un conteneur en plus."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .anomaly import run_batch_detection
from .collectors import collect_hourly
from .mobility import simulate_now
from .predictor import predict_tomorrow

log = logging.getLogger("scheduler")


def _safe(fn, name):
    def run():
        try:
            fn()
            log.info("Tâche %s terminée", name)
        except Exception:
            log.exception("Tâche %s en échec", name)
    return run


def _retrain():
    from ml.train import train
    meta = train()
    log.info("Modèle ré-entraîné : %s", meta["metrics"][meta["best_model"]])


def start() -> BackgroundScheduler:
    s = BackgroundScheduler(timezone="Europe/Paris")
    s.add_job(_safe(collect_hourly, "collecte"), "cron", minute=5)            # toutes les heures à HH:05
    s.add_job(_safe(simulate_now, "mobilite"), "cron", minute="*/15")       # trafic toutes les 15 min
    s.add_job(_safe(predict_tomorrow, "prediction"), "cron", hour="6,18", minute=15)
    s.add_job(_safe(run_batch_detection, "isolation_forest"), "cron", hour=2, minute=0)
    s.add_job(_safe(_retrain, "reentrainement"), "cron", day_of_week="sun", hour=3)
    s.start()
    _safe(simulate_now, "mobilite")()   # une première valeur de trafic dès le démarrage
    return s
