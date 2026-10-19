"""Logs détaillés (US-018) : JSON sur la console (lu par `docker compose logs`)
et dans un fichier tournant /app/logs/app.log (consultable depuis l'admin)."""
import json
import logging
import os
from logging.handlers import RotatingFileHandler

from .config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    os.makedirs(settings.log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    fmt = JsonFormatter()
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    file = RotatingFileHandler(os.path.join(settings.log_dir, "app.log"), maxBytes=5_000_000, backupCount=3)
    file.setFormatter(fmt)
    root.addHandler(console)
    root.addHandler(file)
