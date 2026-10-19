"""Accès aux données : toutes les requêtes SQL de lecture au même endroit."""
import pandas as pd

from ..database import execute, fetch_all, station_id


def save_measurement(time, station_code: str, pollutant: str, value: float, source: str,
                     is_anomaly: bool = False, score: float | None = None) -> None:
    execute(
        """INSERT INTO measurements (time, station_id, pollutant, value, source, is_anomaly, anomaly_score)
           VALUES (:t, :s, :p, :v, :src, :a, :sc)
           ON CONFLICT (time, station_id, pollutant) DO UPDATE SET value = EXCLUDED.value""",
        t=time, s=station_id(station_code), p=pollutant, v=value, src=source, a=is_anomaly, sc=score,
    )


def latest_by_station() -> list[dict]:
    """Dernière valeur de chaque polluant pour chaque station (dashboard + carte)."""
    return fetch_all(
        """SELECT DISTINCT ON (m.station_id, m.pollutant)
                  s.code, s.name, s.zone, s.lat, s.lon, s.kind,
                  m.pollutant, m.value, m.time, m.is_anomaly
           FROM measurements m JOIN stations s ON s.id = m.station_id
           WHERE m.time > now() - interval '1 day'
           ORDER BY m.station_id, m.pollutant, m.time DESC"""
    )


def history(pollutant: str, hours: int = 24) -> list[dict]:
    """Moyenne horaire toutes stations confondues (hors anomalies) -> graphique 24h."""
    return fetch_all(
        """SELECT time_bucket('1 hour', time) AS hour, round(avg(value)::numeric, 1)::float AS value
           FROM measurements
           WHERE pollutant = :p AND NOT is_anomaly AND time > now() - make_interval(hours => :h)
           GROUP BY hour ORDER BY hour""",
        p=pollutant, h=hours,
    )


def recent_values(station_code: str, pollutant: str, hours: int = 24) -> list[float]:
    rows = fetch_all(
        """SELECT value FROM measurements m JOIN stations s ON s.id = m.station_id
           WHERE s.code = :c AND m.pollutant = :p AND NOT m.is_anomaly
             AND m.time > now() - make_interval(hours => :h)""",
        c=station_code, p=pollutant, h=hours,
    )
    return [r["value"] for r in rows]


def neighbours_latest(station_code: str, pollutant: str = "pm25", minutes: int = 45) -> list[dict]:
    """Dernière mesure de chacun des AUTRES capteurs IoT (hors pannes physiques évidentes).
    Sert à distinguer une vraie hausse générale de pollution d'une panne isolée."""
    return fetch_all(
        """SELECT DISTINCT ON (m.station_id) s.code, m.time, m.value, m.is_anomaly, m.anomaly_score
           FROM measurements m JOIN stations s ON s.id = m.station_id
           WHERE s.code <> :c AND s.kind = 'iot' AND m.pollutant = :p
             AND coalesce(m.anomaly_score, 0) < 99
             AND m.time > now() - make_interval(mins => :mn)
           ORDER BY m.station_id, m.time DESC""",
        c=station_code, p=pollutant, mn=minutes,
    )


def unflag(station_code: str, time, pollutant: str = "pm25") -> None:
    execute("""UPDATE measurements SET is_anomaly = FALSE
               WHERE time = :t AND pollutant = :p AND station_id = (SELECT id FROM stations WHERE code = :c)""",
            t=time, p=pollutant, c=station_code)


def hourly_history(days: int = 30) -> pd.DataFrame:
    """PM2.5 moyen horaire + météo, pour le modèle de prédiction."""
    rows = fetch_all(
        """SELECT time_bucket('1 hour', m.time) AS time, avg(m.value) AS pm25,
                  avg(w.temperature) AS temperature, avg(w.humidity) AS humidity,
                  avg(w.wind_speed) AS wind_speed, avg(w.pressure) AS pressure,
                  avg(mo.traffic_index) AS traffic_index
           FROM measurements m
           LEFT JOIN weather w ON w.time = time_bucket('1 hour', m.time)
           LEFT JOIN mobility mo ON mo.time = time_bucket('1 hour', m.time)
           WHERE m.pollutant = 'pm25' AND NOT m.is_anomaly
             AND m.time > now() - make_interval(days => :d)
           GROUP BY 1 ORDER BY 1""",
        d=days,
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        cols = ["temperature", "humidity", "wind_speed", "pressure", "traffic_index"]
        df[cols] = df[cols].astype(float).ffill().bfill()
    return df


def pollution_weather(hours: int = 168) -> list[dict]:
    """PM2.5 et météo alignés heure par heure (US-013 : corrélation)."""
    return fetch_all(
        """SELECT time_bucket('1 hour', m.time) AS hour,
                  round(avg(m.value)::numeric, 1)::float AS pm25,
                  avg(w.temperature) AS temperature, avg(w.wind_speed) AS wind_speed,
                  avg(w.humidity) AS humidity
           FROM measurements m LEFT JOIN weather w ON w.time = time_bucket('1 hour', m.time)
           WHERE m.pollutant = 'pm25' AND NOT m.is_anomaly AND m.time > now() - make_interval(hours => :h)
           GROUP BY hour ORDER BY hour""",
        h=hours,
    )


def thresholds() -> dict[str, float]:
    return {r["pollutant"]: r["value"] for r in fetch_all("SELECT pollutant, value FROM thresholds")}
