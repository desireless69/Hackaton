from __future__ import annotations

import html
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def load_local_env(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env(PROJECT_ROOT / ".env")

from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.parser import parse_bin_log
from telemetry_dashboard.visualization import (
    build_comparison_map_figure,
    build_map_figure,
    build_projection_figures,
    build_trajectory_figure,
)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    canvas = None
    letter = None

app = FastAPI(title="UAV Telemetry Analyzer")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "src" / "templates"))
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "src" / "static")), name="static")
UPLOADS_DIR = PROJECT_ROOT / ".uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def render_ai_html(text: str) -> str:
    sections: list[str] = []
    current_title: str | None = None
    current_body: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            if current_title is not None:
                body_html = " ".join(html.escape(part) for part in current_body)
                sections.append(
                    f'<section class="ai-section"><h3>{html.escape(current_title)}</h3><p>{body_html}</p></section>'
                )
            current_title = line[4:].strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title is not None:
        body_html = " ".join(html.escape(part) for part in current_body)
        sections.append(
            f'<section class="ai-section"><h3>{html.escape(current_title)}</h3><p>{body_html}</p></section>'
        )
    elif text.strip():
        sections.append(f"<p>{html.escape(text.strip())}</p>")

    return "".join(sections)


def cleanup_temp_file(file_path: Path) -> None:
    for _ in range(5):
        try:
            file_path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(0.1)


def cleanup_report_dir(report_dir: Path) -> None:
    if not report_dir.exists():
        return
    for child in report_dir.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)
    report_dir.rmdir()


def create_saved_upload(filename: str, payload: bytes) -> tuple[str, Path]:
    report_id = uuid.uuid4().hex[:12]
    report_dir = UPLOADS_DIR / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    saved_path = report_dir / filename
    saved_path.write_bytes(payload)
    meta = {"report_id": report_id, "filename": filename}
    (report_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return report_id, saved_path


def load_saved_upload(report_id: str) -> tuple[str, Path]:
    report_dir = UPLOADS_DIR / report_id
    meta_path = report_dir / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Saved report not found.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    filename = meta["filename"]
    saved_path = report_dir / filename
    if not saved_path.exists():
        raise HTTPException(status_code=404, detail="Saved log file is missing.")
    return filename, saved_path


def build_report_context(filename: str, report_id: str | None, parsed_flight, report) -> dict[str, object]:
    summary_html = render_ai_html(build_insight(report))
    trajectory_figure = build_trajectory_figure(report.enriched_samples)
    top_view_figure, altitude_figure = build_projection_figures(report.enriched_samples)
    map_figure = build_map_figure(report.enriched_samples)

    return {
        "filename": filename,
        "report_id": report_id,
        "export_url": f"/reports/{report_id}/export.pdf" if report_id else None,
        "metrics": report.metrics.as_dict(),
        "summary_html": summary_html,
        "trajectory_html": trajectory_figure.to_html(full_html=False, include_plotlyjs=False),
        "top_view_html": top_view_figure.to_html(full_html=False, include_plotlyjs=False),
        "altitude_html": altitude_figure.to_html(full_html=False, include_plotlyjs=False),
        "map_html": map_figure.to_html(full_html=False, include_plotlyjs="cdn"),
        "gps_frequency_hz": round(parsed_flight.metadata.gps_frequency_hz, 2),
        "imu_frequency_hz": round(parsed_flight.metadata.imu_frequency_hz, 2),
    }


def build_comparison_rows(label_a: str, label_b: str, report_a, report_b) -> list[dict[str, object]]:
    metrics = [
        ("Total duration", "s", report_a.metrics.total_duration_s, report_b.metrics.total_duration_s),
        ("Total distance", "m", report_a.metrics.total_distance_m, report_b.metrics.total_distance_m),
        ("Max altitude gain", "m", report_a.metrics.max_altitude_gain_m, report_b.metrics.max_altitude_gain_m),
        ("Max horizontal speed", "m/s", report_a.metrics.max_horizontal_speed_m_s, report_b.metrics.max_horizontal_speed_m_s),
        ("Max vertical speed", "m/s", report_a.metrics.max_vertical_speed_m_s, report_b.metrics.max_vertical_speed_m_s),
        ("Max acceleration", "m/s²", report_a.metrics.max_acceleration_m_s2, report_b.metrics.max_acceleration_m_s2),
    ]
    rows: list[dict[str, object]] = []
    for label, unit, value_a, value_b in metrics:
        rows.append(
            {
                "label": label,
                "unit": unit,
                "value_a": value_a,
                "value_b": value_b,
                "delta": value_b - value_a,
                "winner": label_a if value_a >= value_b else label_b,
            }
        )
    return rows


def render_comparison_summary(label_a: str, label_b: str, report_a, report_b) -> str:
    distance_delta = report_b.metrics.total_distance_m - report_a.metrics.total_distance_m
    speed_delta = report_b.metrics.max_horizontal_speed_m_s - report_a.metrics.max_horizontal_speed_m_s
    altitude_delta = report_b.metrics.max_altitude_gain_m - report_a.metrics.max_altitude_gain_m
    return (
        f"{label_b} flew {distance_delta:+.1f} m versus {label_a}, reached "
        f"{speed_delta:+.1f} m/s difference in peak horizontal speed, and changed max altitude gain by "
        f"{altitude_delta:+.1f} m."
    )


def build_pdf_response(filename: str, report) -> Response:
    if canvas is None or letter is None:
        raise HTTPException(status_code=503, detail="PDF export requires reportlab. Run `pip install -r requirements.txt`.")

    buffer_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    buffer_path.close()

    pdf = canvas.Canvas(buffer_path.name, pagesize=letter)
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

    pdf.save()
    pdf_bytes = Path(buffer_path.name).read_bytes()
    cleanup_temp_file(Path(buffer_path.name))
    headers = {"Content-Disposition": f'attachment; filename="{Path(filename).stem}-report.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.get("/", response_class=HTMLResponse)
async def serve_upload_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_class=HTMLResponse)
async def process_telemetry(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    if not file.filename or not file.filename.lower().endswith((".bin", ".log")):
        raise HTTPException(status_code=400, detail="Only .BIN or .log files are supported.")

    payload = await file.read()
    report_id, saved_path = create_saved_upload(file.filename, payload)

    try:
        parsed_flight = parse_bin_log(saved_path)
        report = analyze_flight(parsed_flight)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "request": request,
                **build_report_context(file.filename, report_id, parsed_flight, report),
            },
        )
    except Exception as exc:
        cleanup_report_dir(UPLOADS_DIR / report_id)
        raise HTTPException(status_code=500, detail=f"Error processing log: {exc}") from exc


@app.post("/compare", response_class=HTMLResponse)
async def compare_telemetry(
    request: Request,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    label_a: str = Form("Flight A"),
    label_b: str = Form("Flight B"),
) -> HTMLResponse:
    if not file_a.filename or not file_a.filename.lower().endswith((".bin", ".log")):
        raise HTTPException(status_code=400, detail="Flight A must be a .BIN or .log file.")
    if not file_b.filename or not file_b.filename.lower().endswith((".bin", ".log")):
        raise HTTPException(status_code=400, detail="Flight B must be a .BIN or .log file.")

    suffix_a = Path(file_a.filename).suffix or ".bin"
    suffix_b = Path(file_b.filename).suffix or ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_a) as tmp_a:
        tmp_a.write(await file_a.read())
        tmp_a_path = Path(tmp_a.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_b) as tmp_b:
        tmp_b.write(await file_b.read())
        tmp_b_path = Path(tmp_b.name)

    try:
        parsed_a = parse_bin_log(tmp_a_path)
        parsed_b = parse_bin_log(tmp_b_path)
        report_a = analyze_flight(parsed_a)
        report_b = analyze_flight(parsed_b)
        comparison_map = build_comparison_map_figure(
            report_a.enriched_samples, report_b.enriched_samples, label_a.strip() or "Flight A", label_b.strip() or "Flight B"
        )
        context = {
            "request": request,
            "label_a": label_a.strip() or "Flight A",
            "label_b": label_b.strip() or "Flight B",
            "filename_a": file_a.filename,
            "filename_b": file_b.filename,
            "summary": render_comparison_summary(label_a.strip() or "Flight A", label_b.strip() or "Flight B", report_a, report_b),
            "rows": build_comparison_rows(label_a.strip() or "Flight A", label_b.strip() or "Flight B", report_a, report_b),
            "map_html": comparison_map.to_html(full_html=False, include_plotlyjs="cdn"),
        }
        return templates.TemplateResponse(request=request, name="comparison.html", context=context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing comparison logs: {exc}") from exc
    finally:
        cleanup_temp_file(tmp_a_path)
        cleanup_temp_file(tmp_b_path)


@app.get("/reports/{report_id}/export.pdf")
async def export_report_pdf(report_id: str) -> Response:
    filename, saved_path = load_saved_upload(report_id)
    parsed_flight = parse_bin_log(saved_path)
    report = analyze_flight(parsed_flight)
    return build_pdf_response(filename, report)
