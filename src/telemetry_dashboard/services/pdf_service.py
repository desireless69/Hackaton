from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response

from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.models import FlightReport
from telemetry_dashboard.services.storage_service import cleanup_temp_file

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    canvas = None
    letter = None


def build_pdf_response(filename: str, report: FlightReport) -> Response:
    if canvas is None or letter is None:
        raise HTTPException(
            status_code=503,
            detail="PDF export requires reportlab. Run `pip install -r requirements.txt`.",
        )

    buffer_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    buffer_path.close()

    pdf = canvas.Canvas(buffer_path.name, pagesize=letter)
    _write_pdf_content(pdf, filename, report)
    pdf.save()

    pdf_bytes = Path(buffer_path.name).read_bytes()
    cleanup_temp_file(Path(buffer_path.name))
    headers = {"Content-Disposition": f'attachment; filename="{Path(filename).stem}-report.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


def _write_pdf_content(pdf, filename: str, report: FlightReport) -> None:
    width, height = letter
    y = height - 54

    pdf.setTitle(f"Flight Report - {filename}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, y, f"Flight Report: {filename}")
    y -= 28

    pdf.setFont("Helvetica", 11)
    pdf.drawString(48, y, f"Generated from saved telemetry log {filename}")
    y -= 30

    metrics = [
        ("Total duration", f"{report.metrics.total_duration_s:.1f} s"),
        ("Total distance", f"{report.metrics.total_distance_m:.1f} m"),
        ("Max altitude gain", f"{report.metrics.max_altitude_gain_m:.1f} m"),
        ("Max horizontal speed", f"{report.metrics.max_horizontal_speed_m_s:.1f} m/s"),
        ("Max vertical speed", f"{report.metrics.max_vertical_speed_m_s:.1f} m/s"),
        ("Max acceleration", f"{report.metrics.max_acceleration_m_s2:.1f} m/s^2"),
    ]

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(48, y, "Metrics")
    y -= 22
    pdf.setFont("Helvetica", 11)
    for label, value in metrics:
        pdf.drawString(56, y, f"{label}: {value}")
        y -= 18

    y -= 8
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(48, y, "AI Summary")
    y -= 22
    pdf.setFont("Helvetica", 11)
    summary_text = build_insight(report).replace("### ", "")
    for raw_line in summary_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if y < 64:
            pdf.showPage()
            y = height - 54
            pdf.setFont("Helvetica", 11)
        pdf.drawString(56, y, line[:105])
        y -= 16
