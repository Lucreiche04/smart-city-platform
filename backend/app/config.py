"""Configuration centralisée : tout vient des variables d'environnement (.env).
Pourquoi : aucun secret dans le code ni sur GitHub, et la même image Docker
tourne en local comme sur le VPS."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://smartcity:smartcity@localhost:5432/smartcity"

    aqicn_token: str = "demo"
    openweather_api_key: str = ""
    city_name: str = "Paris"
    city_lat: float = 48.8566
    city_lon: float = 2.3522

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password: str = "admin"
    iot_api_key: str = "dev-iot-key"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "smartcity/sensors/+"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alertes@smartcity.local"
    alert_emails: str = ""

    model_dir: str = "/app/models"
    log_dir: str = "/app/logs"
    data_dir: str = "/app/data"
    enable_background: bool = True   # désactivé pendant les tests

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=("settings_",))


settings = Settings()
