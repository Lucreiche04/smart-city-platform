"""Génère 6 mois de données horaires réalistes (pollution + météo).

À quoi ça sert : le client promet un CSV de 6 mois, mais tant qu'on ne l'a pas,
on ne peut ni tester l'import ni entraîner le modèle. Ce générateur reproduit
les mécanismes physiques connus pour que le modèle ait quelque chose à apprendre :
- saison : plus de PM2.5 en hiver (chauffage, inversions de température)
- cycle journalier : pics aux heures de pointe 8h et 19h (trafic)
- semaine : moins de trafic le week-end
- vent : disperse les particules (corrélation négative)
- persistance : un épisode de pollution dure plusieurs jours (bruit AR(1))

Usage : python -m ml.synthetic --days 180 --out data/historique.csv
"""
import argparse

import numpy as np
import pandas as pd


def generate(days: int = 180, end: str | None = None, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end_ts = pd.Timestamp(end or pd.Timestamp.now(tz="UTC").floor("h"))
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    idx = pd.date_range(end=end_ts, periods=days * 24, freq="h")
    n = len(idx)
    doy = np.asarray(idx.dayofyear)
    hour = np.asarray(idx.hour)
    weekend = np.asarray(idx.dayofweek) >= 5

    # Météo
    temperature = 12 - 8 * np.cos(2 * np.pi * (doy - 15) / 365) + 4 * np.sin(2 * np.pi * (hour - 9) / 24) + rng.normal(0, 1.5, n)
    wind = np.empty(n)
    wind[0] = 4
    for i in range(1, n):  # vent persistant (processus AR(1))
        wind[i] = 0.97 * wind[i - 1] + 0.03 * 4 + rng.normal(0, 0.35)
    wind = np.clip(wind, 0.2, 14)
    humidity = np.clip(75 - 1.2 * (temperature - 12) + rng.normal(0, 6, n), 25, 100)
    pressure = 1015 + 8 * np.sin(2 * np.pi * np.arange(n) / (24 * 6)) + rng.normal(0, 2, n)

    # Pollution
    season = 16 + 9 * np.cos(2 * np.pi * (doy - 15) / 365)
    rush = 1 + 0.35 * np.exp(-((hour - 8) ** 2) / 4) + 0.30 * np.exp(-((hour - 19) ** 2) / 5)
    week = np.where(weekend, 0.8, 1.0)
    dispersion = np.clip(1.5 - 0.09 * wind, 0.4, 1.6)
    stagnation = 1 + 0.004 * (pressure - 1015).clip(0)   # anticyclone = air stagnant
    noise = np.empty(n)
    noise[0] = 0
    for i in range(1, n):
        noise[i] = 0.985 * noise[i - 1] + rng.normal(0, 0.035)
    pm25 = season * rush * week * dispersion * stagnation * np.exp(noise)
    # quelques épisodes de pollution de 2-4 jours
    for _ in range(max(1, days // 45)):
        start = rng.integers(0, n - 96)
        pm25[start:start + rng.integers(48, 96)] *= rng.uniform(1.8, 2.6)
    pm25 = np.clip(pm25 + rng.normal(0, 1.2, n), 1, None)

    traffic = np.clip(45 * rush * week + rng.normal(0, 5, n), 0, 100)
    no2 = np.clip(18 + 0.7 * traffic * dispersion + rng.normal(0, 4, n), 2, None)
    pm10 = pm25 * rng.uniform(1.4, 1.8, n)
    o3 = np.clip(55 + 2.0 * (temperature - 12) - 0.3 * no2 + rng.normal(0, 6, n), 2, None)
    so2 = np.clip(rng.normal(3, 1, n), 0.3, None)

    return pd.DataFrame({
        "time": idx, "pm25": pm25.round(1), "pm10": pm10.round(1), "no2": no2.round(1),
        "o3": o3.round(1), "so2": so2.round(1), "temperature": temperature.round(1),
        "humidity": humidity.round(0), "wind_speed": wind.round(1), "pressure": pressure.round(1),
        "traffic_index": traffic.round(0),
    })


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=180)
    p.add_argument("--out", default="data/historique.csv")
    a = p.parse_args()
    df = generate(a.days)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} lignes écrites dans {a.out}")
