"""Rapport PDF hebdomadaire pour les élus (US-014).
Contenu : chiffres clés de la semaine, graphique PM2.5 vs seuil, alertes, prévision."""
import io
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from ..database import fetch_all  # noqa: E402
from .mobility import impact_sentence  # noqa: E402
from .predictor import latest_prediction  # noqa: E402
from .repository import history, thresholds  # noqa: E402


# Police Unicode (µ, ³, accents) : DejaVu est fournie avec matplotlib, rien à installer.
_FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))


def _styles():
    styles = getSampleStyleSheet()
    for name in ("Normal", "Title", "Heading2"):
        styles[name].fontName = "DejaVu-Bold" if name != "Normal" else "DejaVu"
    return styles


def _chart(points: list[dict], threshold: float) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 2.8), dpi=150)
    ax.plot([p["hour"] for p in points], [p["value"] for p in points], color="#1f6feb", lw=1.4, label="PM2.5")
    ax.axhline(threshold, color="#d63b3b", ls="--", lw=1, label=f"Seuil {threshold:.0f} µg/m³")
    ax.set_ylabel("µg/m³")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def weekly_report() -> bytes:
    styles = _styles()
    stats = fetch_all(
        """SELECT pollutant, round(avg(value)::numeric,1)::float AS moy, round(max(value)::numeric,1)::float AS max
           FROM measurements WHERE NOT is_anomaly AND time > now() - interval '7 days'
             AND pollutant IN ('pm25','pm10','no2') GROUP BY pollutant ORDER BY pollutant""")
    alerts = fetch_all(
        """SELECT a.time, s.name, a.pollutant, a.value FROM alerts a JOIN stations s ON s.id = a.station_id
           WHERE a.time > now() - interval '7 days' ORDER BY a.time DESC LIMIT 15""")
    th = thresholds()
    pred = latest_prediction()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm)
    story = [
        Paragraph("Rapport hebdomadaire — Qualité de l'air", styles["Title"]),
        Paragraph(f"Généré le {datetime.now():%d/%m/%Y à %H:%M} — 7 derniers jours", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Chiffres clés", styles["Heading2"]),
    ]
    table = [["Polluant", "Moyenne (µg/m³)", "Maximum (µg/m³)", "Seuil"]] + [
        [s["pollutant"].upper(), s["moy"], s["max"], th.get(s["pollutant"], "-")] for s in stats]
    t = Table(table, colWidths=[3.5 * cm, 4 * cm, 4 * cm, 3 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                           ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey)]))
    story += [t, Spacer(1, 12), Paragraph("Évolution du PM2.5", styles["Heading2"]),
              Image(_chart(history("pm25", 168), th.get("pm25", 50)), width=16 * cm, height=6.4 * cm)]
    story.append(Paragraph(f"Alertes de la semaine : {len(alerts)}", styles["Heading2"]))
    for a in alerts:
        story.append(Paragraph(f"{a['time']:%d/%m %Hh} — {a['name']} — {a['pollutant'].upper()} "
                               f"{a['value']:.0f} µg/m³", styles["Normal"]))
    sentence = impact_sentence()
    if sentence:
        story += [Paragraph("Trafic et pollution", styles["Heading2"]), Paragraph(sentence, styles["Normal"])]
    if pred:
        story += [Paragraph("Prévision pour demain", styles["Heading2"]),
                  Paragraph(f"PM2.5 attendu : {pred['value']:.0f} µg/m³ (entre {pred['lower_bound']:.0f} et "
                            f"{pred['upper_bound']:.0f}). Fiabilité du modèle : {pred['reliability']:.0f} %. "
                            f"{pred['recommendation']['advice']}", styles["Normal"])]
    doc.build(story)
    return buf.getvalue()
