from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.llm_summary import build_insight
from telemetry_dashboard.parser import parse_bin_log
from telemetry_dashboard.visualization import build_trajectory_figure

st.set_page_config(
    page_title="Telemetry Flight Analyzer",
    page_icon=":airplane:",
    layout="wide",
)


def load_uploaded_file(uploaded_file) -> Path:
    uploads_dir = PROJECT_ROOT / ".uploads"
    uploads_dir.mkdir(exist_ok=True)

    target_path = uploads_dir / uploaded_file.name
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def metrics_table(metrics: dict[str, float | str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Metric": key.replace("_", " ").title(), "Value": value}
            for key, value in metrics.items()
        ]
    )


def render_report(log_path: Path) -> None:
    parsed = parse_bin_log(log_path)
    report = analyze_flight(parsed)

    st.subheader(f"Log: {log_path.name}")
    left, middle, right = st.columns(3)
    left.metric("Duration", f"{report.metrics.total_duration_s:.2f} s")
    middle.metric("Distance", f"{report.metrics.total_distance_m:.2f} m")
    right.metric("Max Altitude Gain", f"{report.metrics.max_altitude_gain_m:.2f} m")

    stat_left, stat_mid, stat_right = st.columns(3)
    stat_left.metric(
        "Max Horizontal Speed",
        f"{report.metrics.max_horizontal_speed_m_s:.2f} m/s",
    )
    stat_mid.metric(
        "Max Vertical Speed",
        f"{report.metrics.max_vertical_speed_m_s:.2f} m/s",
    )
    stat_right.metric(
        "Max Acceleration",
        f"{report.metrics.max_acceleration_m_s2:.2f} m/s^2",
    )

    st.caption(
        "The dashboard still integrates IMU accelerations with the trapezoidal rule, "
        "but the headline speed metrics are taken from GPS because pure IMU integration "
        "accumulates drift. Both views are shown below for transparent comparison."
    )

    chart_col, info_col = st.columns([2, 1])
    with chart_col:
        st.plotly_chart(build_trajectory_figure(report.enriched_samples), use_container_width=True)
    with info_col:
        st.markdown("### Sensor metadata")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Sensor": "GPS",
                        "Rows": parsed.metadata.gps_rows,
                        "Sampling frequency (Hz)": round(parsed.metadata.gps_frequency_hz, 3),
                        "Units": ", ".join(
                            f"{key}={value}" for key, value in parsed.metadata.gps_units.items()
                        ),
                    },
                    {
                        "Sensor": "IMU",
                        "Rows": parsed.metadata.imu_rows,
                        "Sampling frequency (Hz)": round(parsed.metadata.imu_frequency_hz, 3),
                        "Units": ", ".join(
                            f"{key}={value}" for key, value in parsed.metadata.imu_units.items()
                        ),
                    },
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Flight insight")
        st.write(build_insight(report))
        st.markdown("### Speed cross-check")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": "GPS",
                        "Max horizontal speed (m/s)": report.metrics.max_horizontal_speed_m_s,
                        "Max vertical speed (m/s)": report.metrics.max_vertical_speed_m_s,
                    },
                    {
                        "Source": "IMU + trapezoidal integration",
                        "Max horizontal speed (m/s)": report.metrics.max_horizontal_speed_imu_m_s,
                        "Max vertical speed (m/s)": report.metrics.max_vertical_speed_imu_m_s,
                    },
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Summary table")
    st.dataframe(metrics_table(report.metrics.as_dict()), use_container_width=True, hide_index=True)

    st.markdown("### Sample preview")
    st.dataframe(report.enriched_samples.head(50), use_container_width=True)


def main() -> None:
    st.title("ArduPilot Telemetry Analyzer")
    st.write(
        "Upload an ArduPilot `.BIN` log or pick one of the bundled samples to parse telemetry, "
        "compute mission metrics, and inspect the 3D ENU trajectory."
    )

    bundled_logs: list[Path] = []
    for candidate_dir in (
        PROJECT_ROOT / "bin",
        PROJECT_ROOT / "_task" / "test_task_challenge",
        PROJECT_ROOT / "backend" / ".uploads",
    ):
        if candidate_dir.exists():
            bundled_logs.extend(sorted(candidate_dir.glob("*.BIN")))

    deduped_logs: dict[str, Path] = {}
    for path in bundled_logs:
        deduped_logs.setdefault(path.name, path)
    bundled_logs = list(deduped_logs.values())

    with st.sidebar:
        st.header("Input")
        uploaded_file = st.file_uploader("Upload `.BIN` log", type=["bin", "BIN"])
        selected_sample = st.selectbox(
            "Or choose a bundled sample",
            options=["None", *[path.name for path in bundled_logs]],
        )
        st.caption(
            "The dashboard parses GPS, IMU, and ATT messages, estimates sampling rates, "
            "converts WGS-84 coordinates to ENU, and integrates accelerations with the trapezoidal rule."
        )

    if uploaded_file is not None:
        render_report(load_uploaded_file(uploaded_file))
        return

    if selected_sample != "None":
        render_report(next(path for path in bundled_logs if path.name == selected_sample))
        return

    st.info("Select one of the bundled flight logs or upload your own `.BIN` file to begin.")


if __name__ == "__main__":
    main()
