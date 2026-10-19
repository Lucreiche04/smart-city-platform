"""Feature engineering pour prédire le PM2.5 moyen de J+1.

On passe des mesures horaires à des moyennes JOURNALIÈRES : la cible
"PM2.5 à J+1" est une moyenne journalière (c'est aussi ce qu'utilisent l'OMS
et les seuils réglementaires journaliers).

Variables d'entrée demandées par le client et comment on les encode :
- historique 7 jours  -> lag_1 ... lag_7 + moyenne glissante 3 j + écart-type 7 j
- météo               -> PRÉVISION météo de J+1 (température, humidité, vent, pression).
  Pourquoi J+1 et pas J : c'est le vent et la pression de DEMAIN qui dispersent ou
  bloquent les particules demain. En production on utilise l'API "forecast" gratuite
  d'OpenWeatherMap ; à l'entraînement on prend la météo réellement observée à J+1
  (hypothèse "prévision parfaite", à signaler dans le rapport d'analyse).
- trafic (mobilité)   -> trafic moyen ATTENDU à J+1. En production : moyenne des
  4 derniers mêmes jours de semaine (le trafic d'un mardi ressemble aux mardis
  précédents). Variable OPTIONNELLE : si l'historique n'a pas de données de
  trafic (ex. CSV du client sans cette colonne), le modèle s'entraîne sans.
- jour de la semaine  -> jour de la CIBLE (J+1) + indicateur week-end
- saison              -> mois encodé en sinus/cosinus (décembre est "proche" de janvier)
"""
import numpy as np
import pandas as pd

WEATHER_COLS = ["temperature", "humidity", "wind_speed", "pressure"]
TRAFFIC_COL = "traffic_index"
BASE_FEATURES = (
    [f"lag_{i}" for i in range(1, 8)]
    + ["roll_mean_3", "roll_std_7"]
    + [f"fc_{c}" for c in WEATHER_COLS]
    + ["target_dow", "target_weekend", "month_sin", "month_cos"]
)
FEATURES = BASE_FEATURES  # compatibilité


def to_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """hourly : colonnes time, pm25 + colonnes météo (+ traffic_index). Une ligne par jour."""
    df = hourly.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    daily = df.set_index("time").resample("D").mean(numeric_only=True)
    # jours manquants : interpolation limitée à 2 jours, au-delà on laisse vide
    return daily.interpolate(limit=2)


def has_traffic(daily: pd.DataFrame) -> bool:
    """Le trafic n'est utilisé que s'il couvre au moins 80 % des jours."""
    return TRAFFIC_COL in daily and daily[TRAFFIC_COL].notna().mean() >= 0.8


def feature_list(daily: pd.DataFrame) -> list[str]:
    return BASE_FEATURES + (["fc_traffic"] if has_traffic(daily) else [])


def build_features(daily: pd.DataFrame) -> pd.DataFrame:
    """Chaque ligne = le jour J avec tout ce qu'on sait ce jour-là + la cible PM2.5 de J+1."""
    d = daily.copy()
    for i in range(1, 8):
        d[f"lag_{i}"] = d["pm25"].shift(i - 1)          # lag_1 = PM2.5 du jour J lui-même
    d["roll_mean_3"] = d["pm25"].rolling(3).mean()
    d["roll_std_7"] = d["pm25"].rolling(7).std()
    for c in WEATHER_COLS:
        d[f"fc_{c}"] = d[c].shift(-1)                    # météo du jour cible
    if TRAFFIC_COL in d:
        d["fc_traffic"] = d[TRAFFIC_COL].shift(-1)       # trafic du jour cible
    target_day = d.index + pd.Timedelta(days=1)
    d["target_dow"] = target_day.dayofweek
    d["target_weekend"] = (target_day.dayofweek >= 5).astype(int)
    d["month_sin"] = np.sin(2 * np.pi * target_day.month / 12)
    d["month_cos"] = np.cos(2 * np.pi * target_day.month / 12)
    d["target"] = d["pm25"].shift(-1)                    # ce qu'on veut prédire
    return d


def training_set(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    features = feature_list(daily)
    d = build_features(daily).dropna(subset=features + ["target"])
    return d[features], d["target"]


def latest_row(daily: pd.DataFrame, forecast: dict, features: list[str] | None = None) -> pd.DataFrame:
    """Features du dernier jour complet + prévisions de demain -> prédiction de demain.
    forecast : {"temperature":..., "humidity":..., "wind_speed":..., "pressure":..., "traffic_index":...}
    features : la liste utilisée à l'entraînement (lue dans metrics.json)."""
    features = features or BASE_FEATURES
    d = build_features(daily)
    last = d.tail(1).copy()
    for c in WEATHER_COLS:
        last[f"fc_{c}"] = forecast.get(c, daily[c].iloc[-1])
    if "fc_traffic" in features:
        fallback = daily[TRAFFIC_COL].iloc[-7:].mean() if TRAFFIC_COL in daily else 45.0
        last["fc_traffic"] = forecast.get(TRAFFIC_COL) or fallback
    return last[features]
