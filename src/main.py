import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# Import the logic from your telemetry_dashboard package
from telemetry_dashboard.parser import parse_bin_log
from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.visualization import build_trajectory_figure

app = FastAPI(title="UAV Telemetry Analyzer")

# Point FastAPI to your templates folder
templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
async def serve_upload_page(request: Request):
    """Serves the main page with the file upload form."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request}
    )


@app.post("/analyze", response_class=HTMLResponse)
async def process_telemetry(request: Request, file: UploadFile = File(...)):
    """Handles the file upload, runs the pipeline, and returns the dashboard."""

    if not file.filename.lower().endswith(('.bin', '.log')):
        raise HTTPException(status_code=400, detail="Only .BIN or .log files are supported.")

    # Save the uploaded file to a temporary location so pymavlink can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        # 1. Parse the MAVLink log
        parsed_flight = parse_bin_log(tmp_path)

        # 2. Analyze the data (calculates metrics and ENU coordinates)
        report = analyze_flight(parsed_flight)

        # 3. Generate summary insight (LLM or rule-based fallback)
        summary = build_insight(report)

        # 4. Generate the Plotly figure
        fig = build_trajectory_figure(report.enriched_samples)

        # Convert the Plotly figure into raw HTML
        # include_plotlyjs='cdn' ensures the browser fetches the required scripts
        plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

        # 5. Send everything to the result template
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "request": request,
                "filename": file.filename,
                "metrics": report.metrics.as_dict(),
                "summary": summary,
                "plot_html": plot_html
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing log: {str(e)}")

    finally:
        # Clean up the temporary file from the disk
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8070, reload=True)