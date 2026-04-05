from __future__ import annotations

import html

from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.models import FlightReport, ParsedFlight
from telemetry_dashboard.view_models import ComparisonRow, ReportTemplateContext
from telemetry_dashboard.visualization import (
    build_comparison_map_figure,
    build_map_figure,
    build_projection_figures,
    build_trajectory_figure,
)


def format_console_report(report: FlightReport) -> list[str]:
    parsed = report.parsed_flight
    metrics = report.metrics
    return [
        f"GPS frequency: {parsed.metadata.gps_frequency_hz:.2f} Hz",
        f"IMU frequency: {parsed.metadata.imu_frequency_hz:.2f} Hz",
        f"Duration: {metrics.total_duration_s:.2f} s",
        f"Distance: {metrics.total_distance_m:.2f} m",
        f"Max horizontal speed (GPS): {metrics.max_horizontal_speed_m_s:.2f} m/s",
        f"Max vertical speed (GPS): {metrics.max_vertical_speed_m_s:.2f} m/s",
        f"Max horizontal speed (IMU): {metrics.max_horizontal_speed_imu_m_s:.2f} m/s",
        f"Max vertical speed (IMU): {metrics.max_vertical_speed_imu_m_s:.2f} m/s",
        f"Max acceleration: {metrics.max_acceleration_m_s2:.2f} m/s^2",
        f"Max altitude gain: {metrics.max_altitude_gain_m:.2f} m",
    ]


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


def build_report_context(
    filename: str,
    report_id: str | None,
    parsed_flight: ParsedFlight,
    report: FlightReport,
) -> ReportTemplateContext:
    summary_html = render_ai_html(build_insight(report))
    trajectory_figure = build_trajectory_figure(report.enriched_samples)
    top_view_figure, altitude_figure = build_projection_figures(report.enriched_samples)
    map_figure = build_map_figure(report.enriched_samples)

    return ReportTemplateContext(
        filename=filename,
        report_id=report_id,
        export_url=f"/reports/{report_id}/export.pdf" if report_id else None,
        metrics=report.metrics.as_dict(),
        summary_html=summary_html,
        trajectory_html=trajectory_figure.to_html(full_html=False, include_plotlyjs=False),
        top_view_html=top_view_figure.to_html(full_html=False, include_plotlyjs=False),
        altitude_html=altitude_figure.to_html(full_html=False, include_plotlyjs=False),
        map_html=map_figure.to_html(full_html=False, include_plotlyjs="cdn"),
        gps_frequency_hz=round(parsed_flight.metadata.gps_frequency_hz, 2),
        imu_frequency_hz=round(parsed_flight.metadata.imu_frequency_hz, 2),
    )


def build_comparison_rows(
    label_a: str,
    label_b: str,
    report_a: FlightReport,
    report_b: FlightReport,
) -> list[ComparisonRow]:
    metrics = [
        ("Total duration", "s", report_a.metrics.total_duration_s, report_b.metrics.total_duration_s),
        ("Total distance", "m", report_a.metrics.total_distance_m, report_b.metrics.total_distance_m),
        ("Max altitude gain", "m", report_a.metrics.max_altitude_gain_m, report_b.metrics.max_altitude_gain_m),
        ("Max horizontal speed", "m/s", report_a.metrics.max_horizontal_speed_m_s, report_b.metrics.max_horizontal_speed_m_s),
        ("Max vertical speed", "m/s", report_a.metrics.max_vertical_speed_m_s, report_b.metrics.max_vertical_speed_m_s),
        ("Max acceleration", "m/s^2", report_a.metrics.max_acceleration_m_s2, report_b.metrics.max_acceleration_m_s2),
    ]
    rows: list[ComparisonRow] = []
    for label, unit, value_a, value_b in metrics:
        rows.append(
            ComparisonRow(
                label=label,
                unit=unit,
                value_a=value_a,
                value_b=value_b,
                delta=value_b - value_a,
                winner=label_a if value_a >= value_b else label_b,
            )
        )
    return rows


def render_comparison_summary(
    label_a: str,
    label_b: str,
    report_a: FlightReport,
    report_b: FlightReport,
) -> str:
    distance_delta = report_b.metrics.total_distance_m - report_a.metrics.total_distance_m
    speed_delta = report_b.metrics.max_horizontal_speed_m_s - report_a.metrics.max_horizontal_speed_m_s
    altitude_delta = report_b.metrics.max_altitude_gain_m - report_a.metrics.max_altitude_gain_m
    return (
        f"{label_b} flew {distance_delta:+.1f} m versus {label_a}, reached "
        f"{speed_delta:+.1f} m/s difference in peak horizontal speed, and changed max altitude gain by "
        f"{altitude_delta:+.1f} m."
    )


def build_comparison_map_html(
    report_a: FlightReport,
    report_b: FlightReport,
    label_a: str,
    label_b: str,
) -> str:
    comparison_map = build_comparison_map_figure(
        report_a.enriched_samples,
        report_b.enriched_samples,
        label_a,
        label_b,
    )
    return comparison_map.to_html(full_html=False, include_plotlyjs="cdn")
