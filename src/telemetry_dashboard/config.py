from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"


def load_local_env(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True, slots=True)
class AppConfig:
    project_root: Path
    src_root: Path
    templates_dir: Path
    static_dir: Path
    uploads_dir: Path


settings = AppConfig(
    project_root=PROJECT_ROOT,
    src_root=SRC_ROOT,
    templates_dir=SRC_ROOT / "templates",
    static_dir=SRC_ROOT / "static",
    uploads_dir=PROJECT_ROOT / ".uploads",
)
