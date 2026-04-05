from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_SRC = str(PROJECT_ROOT / "src")
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from telemetry_dashboard.config import load_local_env, settings
from telemetry_dashboard.routes import router

load_local_env(settings.project_root / ".env")

app = FastAPI(title="UAV Telemetry Analyzer")
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.include_router(router)
