"""Import du CSV historique (6 mois fourni par le client) dans la base.

Pourquoi : le critère MVP exige 7 jours d'historique minimum en base, et le
modèle a besoin de plusieurs mois. L'API gratuite AQICN ne donne pas
l'historique, donc on amorce la base avec ce fichier.

Colonnes attendues : time, pm25, pm10, no2 [, o3, so2, temperature, humidity, wind_speed, pressure, traffic_index]
Usage : python -m ml.import_csv data/historique.csv
"""
import sys

import pandas as pd
from sqlalchemy import text

from app.database import engine, station_id

POLLUTANT_COLS = ["pm25", "pm10", "no2", "o3", "so2"]
WEATHER_COLS = ["temperature", "humidity", "wind_speed", "pressure"]


def import_csv(path: str) -> int:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    sid = station_id("aqicn-paris")
    long = df.melt(id_vars="time", value_vars=[c for c in POLLUTANT_COLS if c in df],
                   var_name="pollutant", value_name="value").dropna()
    rows = [{"t": r.time, "s": sid, "p": r.pollutant, "v": float(r.value)} for r in long.itertuples()]
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO measurements (time, station_id, pollutant, value, source)
                              VALUES (:t, :s, :p, :v, 'csv') ON CONFLICT DO NOTHING"""), rows)
        if set(WEATHER_COLS) <= set(df.columns):
            w = df[["time"] + WEATHER_COLS].dropna()
            conn.execute(text("""INSERT INTO weather VALUES (:time, :temperature, :humidity, :wind_speed, :pressure)
                                  ON CONFLICT DO NOTHING"""), w.to_dict("records"))
        if "traffic_index" in df:
            m = df[["time", "traffic_index"]].dropna()
            conn.execute(text("""INSERT INTO mobility (time, traffic_index) VALUES (:time, :traffic_index)
                                  ON CONFLICT DO NOTHING"""), m.to_dict("records"))
    return len(rows)


if __name__ == "__main__":
    print(f"{import_csv(sys.argv[1] if len(sys.argv) > 1 else 'data/historique.csv')} mesures importées")
