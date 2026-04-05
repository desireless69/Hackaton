from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

from telemetry_dashboard.config import settings

settings.uploads_dir.mkdir(exist_ok=True)


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
    report_dir = settings.uploads_dir / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    saved_path = report_dir / filename
    saved_path.write_bytes(payload)
    meta = {"report_id": report_id, "filename": filename}
    (report_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return report_id, saved_path


def load_saved_upload(report_id: str) -> tuple[str, Path]:
    report_dir = settings.uploads_dir / report_id
    meta_path = report_dir / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Saved report not found.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    filename = meta["filename"]
    saved_path = report_dir / filename
    if not saved_path.exists():
        raise HTTPException(status_code=404, detail="Saved log file is missing.")
    return filename, saved_path
