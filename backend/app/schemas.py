"""Schémas Pydantic : validation et sanitisation de toutes les entrées.
Une valeur hors bornes ou un champ inconnu est rejeté avec une erreur 422
avant même d'atteindre la base de données."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

POLLUTANTS = {"pm25", "pm10", "no2", "o3", "so2"}


class SensorReading(BaseModel):
    sensor_id: str = Field(pattern=r"^iot-\d{2}$")
    timestamp: datetime
    pm25: float = Field(ge=0, le=1000)
    temperature: float = Field(ge=-40, le=60)
    humidity: float = Field(ge=0, le=100)


class ThresholdUpdate(BaseModel):
    pollutant: str
    value: float = Field(gt=0, le=1000)

    @field_validator("pollutant")
    @classmethod
    def known_pollutant(cls, v: str) -> str:
        if v not in POLLUTANTS:
            raise ValueError(f"Polluant inconnu : {v}")
        return v


class SubscriberIn(BaseModel):
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
