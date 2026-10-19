"""Détection d'anomalies (US-010).

Deux méthodes complémentaires, comme suggéré par le client :
1. Z-score EN LIGNE, à chaque mesure IoT reçue : on compare la valeur aux
   24 dernières heures du même capteur. |z| > 3 -> anomalie (règle des 3 écarts-types).
   Simple, instantané, explicable. Deux garde-fous :
   - plausibilité physique (PM2.5 hors 0,5-500 µg/m³ = panne, même sans historique) ;
   - confirmation par les voisins : si les autres capteurs montent aussi, c'est
     un vrai épisode de pollution, pas une panne (voir mqtt_ingest.process_reading).
2. Isolation Forest EN LOT, une fois par jour : regarde PM2.5 + température +
   humidité ENSEMBLE, donc détecte aussi des combinaisons incohérentes
   (ex. 35 °C avec 100 % d'humidité en hiver). Score normalisé 0-1, seuil 0.7.

Une mesure marquée anomalie est gardée en base (traçabilité) mais exclue
des moyennes, des graphiques et de l'entraînement du modèle.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..database import execute, fetch_all

Z_THRESHOLD = 3.0
IF_THRESHOLD = 0.7


PLAUSIBLE_PM25 = (0.5, 500.0)   # hors de cette plage : capteur en panne, quel que soit l'historique


def zscore(value: float, history: list[float]) -> tuple[bool, float]:
    # Règle de plausibilité : couvre le "démarrage à froid" d'un capteur sans historique
    if not PLAUSIBLE_PM25[0] <= value <= PLAUSIBLE_PM25[1]:
        return True, 99.0
    if len(history) < 8:          # pas assez d'historique pour un calcul statistique fiable
        return False, 0.0
    mean, std = float(np.mean(history)), float(np.std(history))
    if std < 1e-6:
        return False, 0.0
    z = (value - mean) / std
    return abs(z) > Z_THRESHOLD, round(z, 2)


def isolation_forest_scores(df: pd.DataFrame) -> np.ndarray:
    """df : colonnes numériques. Retourne un score 0 (normal) -> 1 (très anormal)."""
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(df)
    raw = -model.score_samples(df)              # plus grand = plus anormal
    return (raw - raw.min()) / (raw.max() - raw.min() + 1e-9)


def run_batch_detection(days: int = 7) -> int:
    rows = fetch_all(
        """SELECT m.time, m.station_id,
                  max(value) FILTER (WHERE pollutant = 'pm25') AS pm25,
                  max(value) FILTER (WHERE pollutant = 'temperature') AS temperature,
                  max(value) FILTER (WHERE pollutant = 'humidity') AS humidity
           FROM measurements m JOIN stations s ON s.id = m.station_id
           WHERE s.kind = 'iot' AND m.time > now() - make_interval(days => :d)
           GROUP BY m.time, m.station_id""",
        d=days,
    )
    df = pd.DataFrame(rows).dropna()
    if len(df) < 50:
        return 0
    df["score"] = isolation_forest_scores(df[["pm25", "temperature", "humidity"]].astype(float))
    flagged = df[df["score"] > IF_THRESHOLD]
    for r in flagged.itertuples():
        execute("""UPDATE measurements SET is_anomaly = TRUE, anomaly_score = :sc
                   WHERE time = :t AND station_id = :s AND pollutant = 'pm25'""",
                sc=float(r.score), t=r.time, s=r.station_id)
    return len(flagged)
