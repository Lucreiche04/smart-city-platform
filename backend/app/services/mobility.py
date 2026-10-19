"""Données de mobilité (source obligatoire n°3 de l'expression de besoin).

Aucune API gratuite ne fournit le trafic parisien en temps réel ; le client
autorise "la génération de données simulées réalistes". Ce module :
1. simule toutes les 15 minutes l'indice de trafic routier (0-100) et la
   fréquentation des transports, avec les vrais rythmes urbains (pointes 8 h et
   18 h, creux la nuit, -20 % le week-end) ;
2. mesure le lien trafic -> pollution sur 30 jours (régression linéaire), pour
   donner aux élus un argumentaire chiffré sur les restrictions de circulation ;
3. fournit la prévision de trafic de demain au modèle IA ;
4. produit un conseil citoyen ("comprendre l'impact de ses déplacements").

En V2 : remplacer simulate_now() par les comptages routiers de data.gouv.fr.
"""
import logging
import math
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np

from ..database import execute, fetch_all, fetch_one

log = logging.getLogger("mobility")
PARIS = ZoneInfo("Europe/Paris")


def traffic_profile(local: datetime) -> tuple[float, int]:
    """Indice de trafic et fréquentation des transports pour une heure locale donnée."""
    h = local.hour + local.minute / 60
    rush = 1 + 0.35 * math.exp(-((h - 8) ** 2) / 4) + 0.30 * math.exp(-((h - 18) ** 2) / 5)
    night = 0.35 if (h < 6 or h >= 23) else 1.0
    week = 0.8 if local.weekday() >= 5 else 1.0
    index = 45 * rush * night * week + random.gauss(0, 4)
    ridership = int(52000 * rush * night * (0.6 if local.weekday() >= 5 else 1.0) * random.uniform(0.9, 1.1))
    return round(min(max(index, 0), 100), 1), ridership


def level(index: float) -> str:
    if index < 35:
        return "fluide"
    if index < 60:
        return "modéré"
    if index < 80:
        return "dense"
    return "saturé"


def simulate_now() -> dict:
    """Écrit (ou met à jour) la ligne de l'heure en cours dans la table mobility."""
    local = datetime.now(PARIS)
    index, ridership = traffic_profile(local)
    hour = local.replace(minute=0, second=0, microsecond=0)
    execute("""INSERT INTO mobility (time, traffic_index, transit_ridership) VALUES (:t, :i, :r)
               ON CONFLICT (time) DO UPDATE SET traffic_index = EXCLUDED.traffic_index,
                                                transit_ridership = EXCLUDED.transit_ridership""",
            t=hour, i=index, r=ridership)
    return {"time": hour, "traffic_index": index, "transit_ridership": ridership}


def series(hours: int = 48) -> list[dict]:
    """Trafic et pollution (NO2, PM2.5) heure par heure."""
    return fetch_all(
        """SELECT mo.time AS hour, mo.traffic_index, mo.transit_ridership,
                  round(avg(m.value) FILTER (WHERE m.pollutant = 'no2')::numeric, 1)::float AS no2,
                  round(avg(m.value) FILTER (WHERE m.pollutant = 'pm25')::numeric, 1)::float AS pm25
           FROM mobility mo
           LEFT JOIN measurements m ON time_bucket('1 hour', m.time) = mo.time AND NOT m.is_anomaly
           WHERE mo.time > now() - make_interval(hours => :h)
           GROUP BY mo.time, mo.traffic_index, mo.transit_ridership ORDER BY mo.time""",
        h=hours,
    )


def impact(days: int = 30) -> dict | None:
    """Pente de la régression pollution ~ trafic : "10 points de trafic en moins = X µg/m³ en moins".
    Attention : c'est une CORRÉLATION, pas une preuve de causalité (le vent et l'heure jouent aussi)."""
    rows = [r for r in series(days * 24) if r["traffic_index"] is not None]
    out = {}
    for pollutant in ("no2", "pm25"):
        pts = [(r["traffic_index"], r[pollutant]) for r in rows if r[pollutant] is not None]
        if len(pts) < 48:
            continue
        x, y = np.array(pts, dtype=float).T
        slope, _ = np.polyfit(x, y, 1)
        r = float(np.corrcoef(x, y)[0, 1])
        out[pollutant] = {"per_10_points": round(float(slope) * 10, 1), "r": round(r, 2), "n_hours": len(pts)}
    return out or None


def tomorrow_traffic() -> float | None:
    """Trafic moyen attendu demain = moyenne des 4 derniers mêmes jours de la semaine."""
    tomorrow = datetime.now(PARIS) + timedelta(days=1)
    row = fetch_one(
        """SELECT avg(traffic_index) AS v FROM mobility
           WHERE extract(isodow FROM time AT TIME ZONE 'Europe/Paris') = :d
             AND time > now() - interval '28 days'""",
        d=tomorrow.isoweekday(),
    )
    return float(row["v"]) if row and row["v"] is not None else None


def citizen_tip(index: float, pm25: float | None) -> str:
    if pm25 is not None and pm25 > 25 and index >= 60:
        return ("Trafic dense et air dégradé : préférez le métro, le RER ou le vélo, et évitez "
                "les grands axes avec les enfants. Chaque trajet en voiture évité réduit les émissions de NO₂.")
    if index >= 60:
        return "Heure de pointe : les transports en commun sont plus rapides et émettent beaucoup moins par voyageur."
    if pm25 is not None and pm25 > 25:
        return "Le trafic est calme mais l'air reste chargé : limitez les efforts physiques prolongés dehors."
    return "Pas d'embouteillage et air correct : bon moment pour un trajet à pied ou à vélo."


def overview(hours: int = 48) -> dict:
    data = series(hours)
    current = next((r for r in reversed(data) if r["traffic_index"] is not None), None)
    pm25 = fetch_one("""SELECT avg(value) AS v FROM measurements WHERE pollutant = 'pm25'
                        AND NOT is_anomaly AND time > now() - interval '2 hours'""")
    pm25_now = float(pm25["v"]) if pm25 and pm25["v"] is not None else None
    result = {"series": data, "impact": impact(), "current": None, "tip": None}
    if current:
        result["current"] = {"traffic_index": current["traffic_index"], "level": level(current["traffic_index"]),
                             "transit_ridership": current["transit_ridership"], "hour": current["hour"]}
        result["tip"] = citizen_tip(current["traffic_index"], pm25_now)
    return result


def impact_sentence() -> str | None:
    """Phrase prête à l'emploi pour le rapport des élus."""
    imp = impact()
    if not imp or "no2" not in imp:
        return None
    n = imp["no2"]
    return (f"Sur les 30 derniers jours, une baisse de 10 points de l'indice de trafic s'accompagne en moyenne "
            f"d'une baisse de {abs(n['per_10_points']):.1f} µg/m³ de NO₂ (corrélation r = {n['r']:.2f}, "
            f"{n['n_hours']} heures analysées). C'est une corrélation, pas une preuve de causalité.")
