"""Alertes email (US-015) avec seuil paramétrable en base.

Anti-spam : une seule alerte par polluant et par station toutes les 3 heures,
sinon un pic qui dure enverrait un email à chaque mesure.
"""
import logging
import smtplib
from email.message import EmailMessage

from ..config import settings
from ..database import execute, fetch_all, fetch_one, station_id
from .recommendations import for_pm25

log = logging.getLogger("alerts")
COOLDOWN_HOURS = 3


def send_email(to: list[str], subject: str, body: str) -> bool:
    if not to:
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, ", ".join(to), subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            if settings.smtp_user:
                s.starttls()
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception:
        log.exception("Envoi email impossible")
        return False


def check(pollutant: str, value: float, station_code: str) -> bool:
    th = fetch_one("SELECT value FROM thresholds WHERE pollutant = :p", p=pollutant)
    if not th or value <= th["value"]:
        return False
    sid = station_id(station_code)
    recent = fetch_one(
        """SELECT 1 FROM alerts WHERE pollutant = :p AND station_id = :s
           AND time > now() - make_interval(hours => :h)""", p=pollutant, s=sid, h=COOLDOWN_HOURS)
    if recent:
        return False
    staff = [e.strip() for e in settings.alert_emails.split(",") if e.strip()]
    citizens = [r["email"] for r in fetch_all("SELECT email FROM subscribers")]
    subject = f"[Alerte pollution] {pollutant.upper()} = {value:.0f} µg/m³ ({station_code})"
    body = (f"Le seuil de {th['value']:.0f} µg/m³ pour {pollutant.upper()} est dépassé "
            f"à la station {station_code} : {value:.1f} µg/m³.\n\n"
            f"Recommandation : {for_pm25(value)['advice']}\n\n"
            "Pour vous désabonner, rendez-vous sur la page Confidentialité de la plateforme.")
    sent = send_email(staff, subject, body)
    for c in citizens:   # un email par citoyen : on ne divulgue pas les adresses entre eux
        send_email([c], subject, body)
    execute("""INSERT INTO alerts (station_id, pollutant, value, threshold, email_sent)
               VALUES (:s, :p, :v, :t, :e)""", s=sid, p=pollutant, v=value, t=th["value"], e=sent)
    log.warning("ALERTE %s=%.1f station=%s email=%s", pollutant, value, station_code, sent)
    return True
