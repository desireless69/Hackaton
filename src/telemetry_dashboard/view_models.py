from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ComparisonRow:
    label: str
    unit: str
    value_a: float
    value_b: float
    delta: float
    winner: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ReportTemplateContext:
    filename: str
    report_id: str | None
    export_url: str | None
    metrics: dict[str, float]
    summary_html: str
    trajectory_html: str
    top_view_html: str
    altitude_html: str
    map_html: str
    gps_frequency_hz: float
    imu_frequency_hz: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
