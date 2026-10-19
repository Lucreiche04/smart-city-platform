"""Recommandations citoyennes selon le niveau de PM2.5 (US-016).
Paliers inspirés de l'indice ATMO (France) et des lignes directrices OMS 2021."""

LEVELS = [
    (10, "bon", "#2e9d5b", "Qualité de l'air bonne. Profitez des activités extérieures."),
    (25, "moyen", "#d6a700", "Qualité correcte. Les personnes très sensibles peuvent limiter les efforts intenses."),
    (50, "dégradé", "#e8792b", "Enfants, personnes âgées et asthmatiques : évitez les efforts prolongés dehors."),
    (75, "mauvais", "#d63b3b", "Réduisez les activités physiques extérieures. Privilégiez les transports en commun."),
    (float("inf"), "très mauvais", "#7d2a8c", "Évitez les sorties non indispensables avec les enfants. Aérez aux heures creuses."),
]


def for_pm25(value: float) -> dict:
    for limit, level, color, advice in LEVELS:
        if value <= limit:
            return {"level": level, "color": color, "advice": advice, "pm25": round(value, 1)}
    return {}
