"""Authentification admin (US-008) : mot de passe haché bcrypt + jeton JWT.
Pourquoi JWT : l'API est sans état (stateless), le frontend React stocke le
jeton en mémoire et l'envoie dans l'en-tête Authorization."""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import settings
from .database import execute, fetch_one

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": username, "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expiré")
    if not username or not fetch_one("SELECT 1 FROM users WHERE username = :u", u=username):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inconnu")
    return username


def require_iot_key(x_api_key: str = Header(...)) -> None:
    """Les capteurs qui postent en HTTP doivent présenter la clé partagée."""
    if x_api_key != settings.iot_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clé capteur invalide")


def audit(actor: str, action: str, request: Request | None = None, details: str = "") -> None:
    """Logs de sécurité : qui a fait quoi, quand, depuis quelle IP."""
    ip = request.client.host if request and request.client else None
    execute(
        "INSERT INTO audit_logs (actor, action, ip, details) VALUES (:a, :ac, :ip, :d)",
        a=actor, ac=action, ip=ip, d=details[:500],
    )


def ensure_admin_user() -> None:
    """Crée le compte admin au premier démarrage à partir du .env."""
    if not fetch_one("SELECT 1 FROM users WHERE username = :u", u=settings.admin_username):
        execute(
            "INSERT INTO users (username, password_hash) VALUES (:u, :h)",
            u=settings.admin_username, h=hash_password(settings.admin_password),
        )
