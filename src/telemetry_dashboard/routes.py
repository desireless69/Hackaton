from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.config import settings
from telemetry_dashboard.parser import parse_bin_log
from telemetry_dashboard.services.pdf_service import build_pdf_response
from telemetry_dashboard.services.report_service import (
    build_comparison_map_html,
    build_comparison_rows,
    build_report_context,
    render_comparison_summary,
)
from telemetry_dashboard.services.storage_service import (
    cleanup_report_dir,
    cleanup_temp_file,
    create_saved_upload,
    load_saved_upload,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.templates_dir))


@router.get("/", response_class=HTMLResponse)
async def serve_upload_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_class=HTMLResponse)
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
            context={"request": request, **build_report_context(file.filename, report_id, parsed_flight, report).to_dict()},
        )
    except Exception as exc:
        cleanup_report_dir(settings.uploads_dir / report_id)
        raise HTTPException(status_code=500, detail=f"Error processing log: {exc}") from exc


@router.post("/compare", response_class=HTMLResponse)
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
    label_a_clean = label_a.strip() or "Flight A"
    label_b_clean = label_b.strip() or "Flight B"

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
        context = {
            "request": request,
            "label_a": label_a_clean,
            "label_b": label_b_clean,
            "filename_a": file_a.filename,
            "filename_b": file_b.filename,
            "summary": render_comparison_summary(label_a_clean, label_b_clean, report_a, report_b),
            "rows": [row.to_dict() for row in build_comparison_rows(label_a_clean, label_b_clean, report_a, report_b)],
            "map_html": build_comparison_map_html(report_a, report_b, label_a_clean, label_b_clean),
        }
        return templates.TemplateResponse(request=request, name="comparison.html", context=context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing comparison logs: {exc}") from exc
    finally:
        cleanup_temp_file(tmp_a_path)
        cleanup_temp_file(tmp_b_path)


@router.get("/reports/{report_id}/export.pdf")
async def export_report_pdf(report_id: str) -> Response:
    filename, saved_path = load_saved_upload(report_id)
    parsed_flight = parse_bin_log(saved_path)
    report = analyze_flight(parsed_flight)
    return build_pdf_response(filename, report)
