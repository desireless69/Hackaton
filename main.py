from __future__ import annotations

import html
import os
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
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
from telemetry_dashboard.visualization import build_projection_figures, build_trajectory_figure

app = FastAPI(title="UAV Telemetry Analyzer")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "src" / "templates"))


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

    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        parsed_flight = parse_bin_log(tmp_path)
        report = analyze_flight(parsed_flight)
        summary_html = render_ai_html(build_insight(report))
        trajectory_figure = build_trajectory_figure(report.enriched_samples)
        top_view_figure, altitude_figure = build_projection_figures(report.enriched_samples)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "request": request,
                "filename": file.filename,
                "metrics": report.metrics.as_dict(),
                "summary_html": summary_html,
                "trajectory_html": trajectory_figure.to_html(full_html=False, include_plotlyjs="cdn"),
                "top_view_html": top_view_figure.to_html(full_html=False, include_plotlyjs=False),
                "altitude_html": altitude_figure.to_html(full_html=False, include_plotlyjs=False),
                "gps_frequency_hz": round(parsed_flight.metadata.gps_frequency_hz, 2),
                "imu_frequency_hz": round(parsed_flight.metadata.imu_frequency_hz, 2),
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing log: {exc}") from exc
    finally:
        cleanup_temp_file(tmp_path)
