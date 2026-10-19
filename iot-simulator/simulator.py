"""Simulateur de 3 capteurs IoT virtuels (US-003).

Chaque capteur publie toutes les 15 minutes (SIM_INTERVAL_SECONDS) un JSON :
  {"sensor_id": "iot-01", "timestamp": "...", "pm25": 18.4, "temperature": 14.2, "humidity": 71}
sur le topic MQTT "smartcity/sensors/<sensor_id>".

Réalisme :
- chaque quartier a son niveau de base (le 18e, plus routier, est plus pollué) ;
- cycle journalier avec pics à 8h et 19h ;
- de temps en temps une valeur aberrante (capteur défectueux) pour tester la
  détection d'anomalies ;
- variable DEMO_PEAK=1 : force un pic de pollution pour la démo d'alerte.

Mode HTTP (si MQTT indisponible) : SIM_MODE=http -> POST /api/ingest avec la clé X-API-Key.
"""
import json
import logging
import math
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("simulator")

SENSORS = {"iot-01": 1.25, "iot-02": 1.0, "iot-03": 0.85}   # facteur de pollution par quartier
INTERVAL = int(os.getenv("SIM_INTERVAL_SECONDS", "900"))
SPIKE_P = float(os.getenv("SIM_SPIKE_PROBABILITY", "0.03"))
MODE = os.getenv("SIM_MODE", "mqtt")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
API_URL = os.getenv("API_URL", "http://backend:8000/api/ingest")
API_KEY = os.getenv("IOT_API_KEY", "dev-iot-key")


def reading(sensor_id: str, factor: float, now: datetime) -> dict:
    h = now.hour + now.minute / 60
    rush = 1 + 0.35 * math.exp(-((h - 8) ** 2) / 4) + 0.30 * math.exp(-((h - 19) ** 2) / 5)
    weekend = 0.8 if now.weekday() >= 5 else 1.0
    pm25 = 15 * factor * rush * weekend * random.lognormvariate(0, 0.15)
    if os.getenv("DEMO_PEAK") == "1":
        pm25 = random.uniform(60, 90)                      # pic réaliste mais au-dessus du seuil 50
    elif random.random() < SPIKE_P:
        pm25 = random.choice([random.uniform(400, 900), 0.0])  # panne de capteur
    temp = 12 + 5 * math.sin(2 * math.pi * (h - 9) / 24) + random.gauss(0, 0.8)
    return {
        "sensor_id": sensor_id,
        "timestamp": now.isoformat(),
        "pm25": round(pm25, 1),
        "temperature": round(temp, 1),
        "humidity": round(min(100, max(20, 75 - 1.2 * (temp - 12) + random.gauss(0, 4)))),
    }


def main() -> None:
    client = None
    if MODE == "mqtt":
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="iot-simulator")
        while True:
            try:
                client.connect(MQTT_HOST, 1883)
                break
            except OSError:
                log.info("Broker MQTT pas prêt, nouvel essai dans 3 s")
                time.sleep(3)
        client.loop_start()
    log.info("Simulateur démarré : %d capteurs, toutes les %d s, mode %s", len(SENSORS), INTERVAL, MODE)
    while True:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        for sid, factor in SENSORS.items():
            payload = reading(sid, factor, now)
            try:
                if client:
                    client.publish(f"smartcity/sensors/{sid}", json.dumps(payload), qos=1)
                else:
                    requests.post(API_URL, json=payload, headers={"X-API-Key": API_KEY}, timeout=10)
                log.info("Envoyé %s", payload)
            except Exception as exc:
                log.warning("Échec d'envoi %s : %s", sid, exc)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
