# Plateforme Smart City — Qualité de l'air et mobilité

Surveillance en temps réel de la qualité de l'air de Paris, prévision du PM2.5 à J+1,
alertes email et rapport PDF pour les élus. Projet ESIC — Master Chef de Projet Data & IA.

## Fonctionnalités (user stories couvertes)

| US | Fonctionnalité | Où |
|---|---|---|
| 001 | Collecte horaire AQICN + OpenWeatherMap | `backend/app/services/collectors.py` |
| 002 | Stockage PostgreSQL + TimescaleDB | `db/init.sql` |
| 003 | 3 capteurs IoT simulés via MQTT (ou HTTP POST) | `iot-simulator/`, `mqtt_ingest.py` |
| 004-006 | Dashboard, filtre par polluant, courbe 24 h | `frontend/src/` |
| 007 | HTTPS automatique | `caddy/Caddyfile` |
| 008 | Authentification admin JWT | `backend/app/security.py` |
| 009, 011 | Prévision J+1 + fiabilité | `backend/ml/`, `predictor.py` |
| 010 | Détection d'anomalies (z-score + Isolation Forest) | `anomaly.py` |
| 012 | Carte interactive | `AirMap.jsx` |
| 013 | Corrélation pollution / météo | `CorrelationChart.jsx` |
| 014 | Rapport PDF hebdomadaire | `report_pdf.py` |
| 015 | Alerte email, seuil paramétrable | `alerts.py`, page Admin |
| 016 | Recommandations citoyennes | `recommendations.py` |
| 017 | Monitoring Prometheus + Grafana | `monitoring/` |
| 018 | Logs JSON consultables dans l'admin | `logging_conf.py` |
| 019 | Responsive mobile | `styles.css` |

## Architecture

```
Capteurs IoT simulés ──MQTT──> Mosquitto ──> Backend FastAPI ──> PostgreSQL/TimescaleDB
AQICN / OpenWeatherMap ──(toutes les heures)──┘     │  ├─ modèle PM2.5 J+1 (scikit-learn)
                                                    │  ├─ alertes email (SMTP)
Navigateur ──HTTPS──> Caddy ──/api──────────────────┘  └─ rapport PDF
                          └──/────> Frontend React (Nginx)
Prometheus ──/metrics──> Backend ; Grafana ──> Prometheus + base
```

## Démarrage rapide (local)

Prérequis : Docker Desktop.

```bash
cp .env.example .env          # puis remplir AQICN_TOKEN, OPENWEATHER_API_KEY, mots de passe
# Optionnel : déposer le CSV historique fourni par le client dans data/historique.csv
docker compose up -d --build
```

| Service | URL |
|---|---|
| Application | https://localhost (accepter le certificat local) |
| Documentation API (Swagger) | https://localhost/docs |
| Grafana | https://localhost/grafana (admin / GRAFANA_PASSWORD) |
| Emails reçus (Mailpit) | http://localhost:8025 |

Au premier démarrage le backend importe l'historique (CSV fourni, ou 180 jours
synthétiques s'il n'y en a pas) et entraîne un premier modèle.

## Commandes utiles

```bash
docker compose logs -f backend                             # suivre les logs
docker compose exec backend python -m ml.train             # ré-entraîner le modèle
docker compose exec backend python -m ml.import_csv data/historique.csv
docker compose exec backend pytest -q                      # tests
docker compose exec db psql -U smartcity                   # console SQL
```

### Démo d'alerte (scénario 2 de la démo finale)
```bash
docker compose run --rm -e DEMO_PEAK=1 -e SIM_INTERVAL_SECONDS=10 iot-simulator
```
Les 3 capteurs envoient un pic de 60 à 90 µg/m³ : l'alerte apparaît dans l'admin
et l'email arrive dans Mailpit (http://localhost:8025).

## Déploiement sur le VPS
1. Faire pointer un nom de domaine (ex. DuckDNS, gratuit) vers l'IP du VPS.
2. `git clone` du dépôt, `cp .env.example .env`, mettre `DOMAIN=mon-domaine.duckdns.org`.
3. Ouvrir uniquement les ports 22, 80 et 443 (`ufw allow 22,80,443/tcp && ufw enable`).
4. `docker compose up -d --build` : Caddy obtient le certificat Let's Encrypt tout seul.
5. Supprimer la ligne `ports: ["8025:8025"]` de Mailpit et configurer un vrai SMTP (Brevo ou Gmail avec mot de passe d'application).

## Tests
- Unitaires : `cd backend && pytest -q` (conversion AQI, anomalies, validation, précision du modèle > 70 %).
- Charge : `locust -f loadtest/locustfile.py --host https://localhost --users 50 --spawn-rate 10 --run-time 2m --headless`.

## Documentation
- API : Swagger sur `/docs` (générée par FastAPI).
- RGPD : `docs/registre-traitements.md`.
- Évolutions : `docs/backlog-v2.md`.
