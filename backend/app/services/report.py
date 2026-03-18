"""PDF report generator — adherence reports, doctor reports.

Uses WeasyPrint to generate PDF from HTML templates.
Gracefully falls back to plain-text if WeasyPrint is unavailable.
"""

import io
import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import Measurement, MoodLog
from app.models.medication import DoseLog, DoseStatus, Medication

logger = logging.getLogger(__name__)


async def generate_adherence_report(
    db: AsyncSession,
    user_id: UUID,
    user_name: str,
    days: int = 30,
) -> tuple[bytes, str]:
    """Generate a medication adherence report as PDF.

    Args:
        db: Async database session.
        user_id: Patient's user ID.
        user_name: Patient's display name.
        days: Number of days to cover.

    Returns:
        Tuple of (pdf_bytes, filename).
    """
    since = date.today() - timedelta(days=days)
    today = date.today()

    # Fetch medications
    meds_result = await db.execute(
        select(Medication).where(
            and_(Medication.user_id == user_id, Medication.is_active == True)
        ).order_by(Medication.name)
    )
    medications = meds_result.scalars().all()

    # Fetch dose logs
    logs_result = await db.execute(
        select(DoseLog).where(
            and_(DoseLog.user_id == user_id, DoseLog.scheduled_date >= since)
        ).order_by(DoseLog.scheduled_date.desc())
    )
    dose_logs = logs_result.scalars().all()

    # Fetch recent measurements
    measurements_result = await db.execute(
        select(Measurement).where(
            and_(Measurement.user_id == user_id, Measurement.created_at >= since.isoformat())
        ).order_by(Measurement.created_at.desc()).limit(50)
    )
    measurements = measurements_result.scalars().all()

    # Calculate adherence stats
    med_stats = []
    for med in medications:
        taken = sum(1 for l in dose_logs if str(l.medication_id) == str(med.id) and l.status == DoseStatus.taken)
        missed = sum(1 for l in dose_logs if str(l.medication_id) == str(med.id) and l.status == DoseStatus.missed)
        skipped = sum(1 for l in dose_logs if str(l.medication_id) == str(med.id) and l.status == DoseStatus.skipped)
        total = taken + missed + skipped
        adherence = round((taken / total * 100) if total > 0 else 0, 1)

        med_stats.append({
            "name": med.name,
            "form": med.form.value if med.form else "tablet",
            "dose": f"{med.dose_amount or ''} {med.dose_unit or ''}".strip(),
            "frequency": med.frequency.value if med.frequency else "daily",
            "taken": taken,
            "missed": missed,
            "skipped": skipped,
            "total": total,
            "adherence": adherence,
        })

    overall_taken = sum(s["taken"] for s in med_stats)
    overall_total = sum(s["total"] for s in med_stats)
    overall_adherence = round((overall_taken / overall_total * 100) if overall_total > 0 else 0, 1)

    # Build HTML
    html = _build_report_html(
        patient_name=user_name,
        period_start=since,
        period_end=today,
        med_stats=med_stats,
        overall_adherence=overall_adherence,
        measurements=measurements,
    )

    # Generate PDF
    pdf_bytes = _html_to_pdf(html)
    filename = f"adherence_report_{user_name.replace(' ', '_')}_{today.isoformat()}.pdf"

    return pdf_bytes, filename


def _build_report_html(
    patient_name: str,
    period_start: date,
    period_end: date,
    med_stats: list,
    overall_adherence: float,
    measurements: list,
) -> str:
    """Build HTML content for the adherence report."""

    # Medication rows
    med_rows = ""
    for s in med_stats:
        color = "#059669" if s["adherence"] >= 80 else "#d97706" if s["adherence"] >= 50 else "#dc2626"
        med_rows += f"""
        <tr>
            <td>{s['name']}</td>
            <td>{s['dose']}</td>
            <td>{s['frequency']}</td>
            <td>{s['taken']}</td>
            <td>{s['missed']}</td>
            <td>{s['skipped']}</td>
            <td style="color:{color};font-weight:bold">{s['adherence']}%</td>
        </tr>"""

    # Measurement rows
    measurement_rows = ""
    for m in measurements[:20]:
        val = f"{m.value1}"
        if m.value2:
            val += f"/{m.value2}"
        measurement_rows += f"""
        <tr>
            <td>{m.type.value if hasattr(m.type, 'value') else m.type}</td>
            <td>{val} {m.unit}</td>
            <td>{m.notes or '-'}</td>
            <td>{str(m.created_at)[:16]}</td>
        </tr>"""

    overall_color = "#059669" if overall_adherence >= 80 else "#d97706" if overall_adherence >= 50 else "#dc2626"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
        h1 {{ color: #059669; border-bottom: 2px solid #059669; padding-bottom: 10px; }}
        h2 {{ color: #374151; margin-top: 30px; }}
        .header {{ display: flex; justify-content: space-between; }}
        .stat-box {{ background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; margin: 10px; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: {overall_color}; }}
        .stat-label {{ color: #6b7280; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #059669; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #e5e7eb; }}
        tr:nth-child(even) {{ background: #f9fafb; }}
        .footer {{ margin-top: 40px; color: #9ca3af; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <h1>Dawai Yaad — Medication Report</h1>

    <p><strong>Patient:</strong> {patient_name}<br>
    <strong>Period:</strong> {period_start} to {period_end}<br>
    <strong>Generated:</strong> {date.today()}</p>

    <div class="stat-box">
        <div class="stat-value">{overall_adherence}%</div>
        <div class="stat-label">Overall Adherence</div>
    </div>

    <h2>Medication Adherence</h2>
    <table>
        <tr>
            <th>Medication</th>
            <th>Dose</th>
            <th>Frequency</th>
            <th>Taken</th>
            <th>Missed</th>
            <th>Skipped</th>
            <th>Adherence</th>
        </tr>
        {med_rows}
    </table>

    {"<h2>Recent Health Measurements</h2>" + '''
    <table>
        <tr><th>Type</th><th>Value</th><th>Notes</th><th>Date</th></tr>
    ''' + measurement_rows + "</table>" if measurement_rows else ""}

    <div class="footer">
        Generated by Dawai Yaad — Open-source Family Health Platform<br>
        This report is auto-generated and should be reviewed by a healthcare professional.
    </div>
</body>
</html>"""


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML to PDF using WeasyPrint, with fallback."""
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        return pdf
    except Exception as e:
        logger.warning(f"WeasyPrint unavailable ({e}), returning HTML as bytes")
        return html.encode("utf-8")
