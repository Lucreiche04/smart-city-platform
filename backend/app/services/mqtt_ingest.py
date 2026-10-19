"""Abonné MQTT (US-003) : reçoit les mesures des capteurs IoT en temps réel.

Flux : capteur -> publie sur "smartcity/sensors/iot-01" -> Mosquitto -> ce module
-> validation Pydantic -> z-score -> base de données -> vérification des seuils.
"""
import json
import logging

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from ..config import settings
from ..schemas import SensorReading
from . import alerts
from .anomaly import zscore
from .repository import neighbours_latest, recent_values, save_measurement, unflag

log = logging.getLogger("mqtt")


def process_reading(reading: SensorReading, source: str = "iot") -> dict:
    """Utilisé par MQTT ET par l'endpoint HTTP POST : une seule logique d'ingestion."""
    is_anom, z = zscore(reading.pm25, recent_values(reading.sensor_id, "pm25"))
    if is_anom and abs(z) < 99:
        # Le z-score seul confond panne et vrai pic. Si au moins un autre capteur mesure
        # aussi une valeur élevée (>= 60 % de celle-ci), c'est un épisode réel :
        # on valide cette mesure ET on "réhabilite" les voisins qui avaient été
        # marqués à tort parce qu'ils avaient détecté la hausse en premier.
        confirming = [n for n in neighbours_latest(reading.sensor_id) if n["value"] >= 0.6 * reading.pm25]
        if confirming:
            is_anom = False
            for n in confirming:
                if n["is_anomaly"]:
                    unflag(n["code"], n["time"])
                    alerts.check("pm25", n["value"], n["code"])
    save_measurement(reading.timestamp, reading.sensor_id, "pm25", reading.pm25, source, is_anom, z)
    save_measurement(reading.timestamp, reading.sensor_id, "temperature", reading.temperature, source)
    save_measurement(reading.timestamp, reading.sensor_id, "humidity", reading.humidity, source)
    if is_anom:
        log.warning("Anomalie %s : pm25=%.1f z=%.2f (ignorée pour les alertes)", reading.sensor_id, reading.pm25, z)
    else:
        alerts.check("pm25", reading.pm25, reading.sensor_id)
    return {"anomaly": is_anom, "zscore": z}


def _on_message(client, userdata, msg):
    try:
        reading = SensorReading(**json.loads(msg.payload))
        process_reading(reading)
    except (ValidationError, json.JSONDecodeError) as exc:
        log.warning("Message MQTT rejeté sur %s : %s", msg.topic, exc)
    except Exception:
        log.exception("Erreur de traitement MQTT")


def _on_connect(client, userdata, flags, reason_code, properties=None):
    log.info("Connecté au broker MQTT (%s), abonnement à %s", reason_code, settings.mqtt_topic)
    client.subscribe(settings.mqtt_topic, qos=1)


def start() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smartcity-backend")
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(settings.mqtt_host, settings.mqtt_port)
    client.loop_start()     # thread réseau en arrière-plan, ne bloque pas l'API
    return client
