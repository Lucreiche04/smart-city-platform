"""Connexion à PostgreSQL/TimescaleDB.
On utilise SQLAlchemy Core + SQL explicite : les requêtes temps-série
(time_bucket, agrégats) s'écrivent plus clairement en SQL qu'avec un ORM."""
from contextlib import contextmanager

from sqlalchemy import create_engine, text

from .config import settings

engine = create_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)


@contextmanager
def get_conn():
    """Connexion transactionnelle : commit automatique si tout va bien, rollback sinon."""
    with engine.begin() as conn:
        yield conn


def fetch_all(sql: str, **params) -> list[dict]:
    with get_conn() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql), params)]


def fetch_one(sql: str, **params) -> dict | None:
    rows = fetch_all(sql, **params)
    return rows[0] if rows else None


def execute(sql: str, **params) -> None:
    with get_conn() as conn:
        conn.execute(text(sql), params)


def station_id(code: str) -> int | None:
    row = fetch_one("SELECT id FROM stations WHERE code = :c", c=code)
    return row["id"] if row else None
