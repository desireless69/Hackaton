from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
UPLOADS_ROOT = PROJECT_ROOT / ".uploads"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas
except ModuleNotFoundError:
    A4 = None
    simpleSplit = None
    canvas = None


def load_local_env(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
    return cleaned or "flight-log.bin"


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


load_local_env(PROJECT_ROOT / ".env")
UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.parser import parse_bin_log
from telemetry_dashboard.visualization import (
    build_comparison_map_figure,
    build_map_figure,
    build_projection_figures,
    build_trajectory_figure,
)

app = FastAPI(title="UAV Telemetry Analyzer")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "src" / "templates"))
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "src" / "static")), name="static")

METRIC_LABELS = {
    "total_duration_s": "Total Duration (s)",
    "total_distance_m": "Total Distance (m)",
    "max_altitude_gain_m": "Max Altitude Gain (m)",
    "max_horizontal_speed_m_s": "Max Horizontal Speed (m/s)",
    "max_vertical_speed_m_s": "Max Vertical Speed (m/s)",
    "max_horizontal_speed_imu_m_s": "Max Horizontal Speed IMU (m/s)",
    "max_vertical_speed_imu_m_s": "Max Vertical Speed IMU (m/s)",
    "max_acceleration_m_s2": "Max Acceleration (m/s^2)",
}


def ensure_supported_file(upload: UploadFile) -> None:
    if not upload.filename or not upload.filename.lower().endswith((".bin", ".log")):
        raise HTTPException(status_code=400, detail="Only .BIN or .log files are supported.")


async def persist_upload(upload: UploadFile) -> tuple[str, Path, str]:
    ensure_supported_file(upload)
    report_id = uuid4().hex
    report_dir = UPLOADS_ROOT / report_id
    report_dir.mkdir(parents=True, exist_ok=True)

    original_filename = sanitize_filename(upload.filename or "flight-log.bin")
    stored_path = report_dir / f"source{Path(original_filename).suffix or '.bin'}"
    stored_path.write_bytes(await upload.read())
    (report_dir / "meta.json").write_text(
        json.dumps({"filename": original_filename}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return report_id, stored_path, original_filename


def load_saved_upload(report_id: str) -> tuple[Path, str]:
    report_dir = UPLOADS_ROOT / report_id
    meta_path = report_dir / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Saved report not found.")

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    source_files = [path for path in report_dir.iterdir() if path.name.startswith("source.")]
    if not source_files:
        raise HTTPException(status_code=404, detail="Saved report source file is missing.")

    return source_files[0], metadata.get("filename", source_files[0].name)


def analyze_log(log_path: Path, display_name: str) -> dict[str, object]:
    parsed_flight = parse_bin_log(log_path)
    report = analyze_flight(parsed_flight)
    summary_text = build_insight(report)
    trajectory_figure = build_trajectory_figure(report.enriched_samples)
    top_view_figure, altitude_figure = build_projection_figures(report.enriched_samples)
    map_figure = build_map_figure(report.enriched_samples)

    return {
        "filename": display_name,
        "report": report,
        "summary_text": summary_text,
        "summary_html": render_ai_html(summary_text),
        "metrics": report.metrics.as_dict(),
        "trajectory_html": trajectory_figure.to_html(full_html=False, include_plotlyjs="cdn"),
        "top_view_html": top_view_figure.to_html(full_html=False, include_plotlyjs=False),
        "altitude_html": altitude_figure.to_html(full_html=False, include_plotlyjs=False),
        "map_html": map_figure.to_html(full_html=False, include_plotlyjs=False),
        "gps_frequency_hz": round(parsed_flight.metadata.gps_frequency_hz, 2),
        "imu_frequency_hz": round(parsed_flight.metadata.imu_frequency_hz, 2),
    }


def build_comparison_rows(metrics_a: dict[str, float], metrics_b: dict[str, float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key, label in METRIC_LABELS.items():
        first = float(metrics_a[key])
        second = float(metrics_b[key])
        delta = second - first
        rows.append(
            {
                "label": label,
                "first": first,
                "second": second,
                "delta": delta,
                "delta_text": f"{delta:+.2f}",
                "trend": "up" if delta > 0 else "down" if delta < 0 else "flat",
            }
        )
    return rows


def build_pdf_response(filename: str, metrics: dict[str, float], summary_text: str) -> StreamingResponse:
    if canvas is None or A4 is None or simpleSplit is None:
        raise HTTPException(
            status_code=503,
            detail="PDF export requires reportlab. Run: pip install -r requirements.txt",
        )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 56

    pdf.setTitle(f"Flight report - {filename}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, y, "UAV Telemetry Report")
    y -= 28

    pdf.setFont("Helvetica", 11)
    pdf.drawString(48, y, f"File: {filename}")
    y -= 26

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(48, y, "Metrics")
    y -= 18
    pdf.setFont("Helvetica", 11)

    for key, label in METRIC_LABELS.items():
        pdf.drawString(56, y, f"{label}: {metrics[key]:.2f}")
        y -= 16
        if y < 96:
            pdf.showPage()
            y = height - 56
            pdf.setFont("Helvetica", 11)

    y -= 10
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(48, y, "AI Summary")
    y -= 20
    pdf.setFont("Helvetica", 11)

    for raw_line in summary_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        wrapped_lines = simpleSplit(line, "Helvetica", 11, width - 96)
        for wrapped in wrapped_lines:
            pdf.drawString(56, y, wrapped)
            y -= 15
            if y < 72:
                pdf.showPage()
                y = height - 56
                pdf.setFont("Helvetica", 11)

    pdf.save()
    buffer.seek(0)

    download_name = f"{Path(filename).stem or 'flight-report'}-report.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@app.get("/", response_class=HTMLResponse)
async def serve_upload_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_class=HTMLResponse)
async def process_telemetry(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    report_id, stored_path, original_filename = await persist_upload(file)

    try:
        context = analyze_log(stored_path, original_filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing log: {exc}") from exc

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"request": request, "report_id": report_id, **context},
    )


@app.get("/report/{report_id}/export/pdf")
async def export_report_pdf(report_id: str) -> StreamingResponse:
    stored_path, filename = load_saved_upload(report_id)

    try:
        context = analyze_log(stored_path, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error exporting report: {exc}") from exc

    return build_pdf_response(
        filename=filename,
        metrics=context["metrics"],
        summary_text=context["summary_text"],
    )


@app.post("/compare", response_class=HTMLResponse)
async def compare_telemetry(
    request: Request,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    compare_label_a: str = Form("Flight A"),
    compare_label_b: str = Form("Flight B"),
) -> HTMLResponse:
    ensure_supported_file(file_a)
    ensure_supported_file(file_b)

    suffix_a = Path(file_a.filename or "flight-a.bin").suffix or ".bin"
    suffix_b = Path(file_b.filename or "flight-b.bin").suffix or ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_a) as tmp_a:
        tmp_a.write(await file_a.read())
        tmp_path_a = Path(tmp_a.name)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_b) as tmp_b:
        tmp_b.write(await file_b.read())
        tmp_path_b = Path(tmp_b.name)

    label_a = compare_label_a.strip() or Path(file_a.filename or "Flight A").stem
    label_b = compare_label_b.strip() or Path(file_b.filename or "Flight B").stem

    try:
        context_a = analyze_log(tmp_path_a, file_a.filename or "Flight A")
        context_b = analyze_log(tmp_path_b, file_b.filename or "Flight B")
        comparison_rows = build_comparison_rows(context_a["metrics"], context_b["metrics"])
        comparison_map = build_comparison_map_figure(
            context_a["report"].enriched_samples,
            context_b["report"].enriched_samples,
            label_a,
            label_b,
        )
        return templates.TemplateResponse(
            request=request,
            name="comparison.html",
            context={
                "request": request,
                "label_a": label_a,
                "label_b": label_b,
                "context_a": context_a,
                "context_b": context_b,
                "comparison_rows": comparison_rows,
                "comparison_map_html": comparison_map.to_html(full_html=False, include_plotlyjs="cdn"),
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error comparing logs: {exc}") from exc
    finally:
        cleanup_temp_file(tmp_path_a)
        cleanup_temp_file(tmp_path_b)
