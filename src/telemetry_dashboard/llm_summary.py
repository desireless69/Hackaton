from __future__ import annotations

import os
from textwrap import dedent

from telemetry_dashboard.models import FlightReport

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


def _rule_based_summary(report: FlightReport) -> str:
    metrics = report.metrics
    risk_flags: list[str] = []

    if metrics.max_vertical_speed_m_s > 20:
        risk_flags.append("the flight had aggressive vertical manoeuvres")
    if metrics.max_horizontal_speed_m_s > 30:
        risk_flags.append("horizontal speed reached a high envelope")
    if metrics.max_acceleration_m_s2 > 15:
        risk_flags.append("acceleration peaks suggest intense dynamic loading")

    verdict = "; ".join(risk_flags) if risk_flags else "the flight stayed within a moderate dynamic envelope"
    return (
        f"Duration {metrics.total_duration_s:.2f} s, distance {metrics.total_distance_m:.2f} m, "
        f"max horizontal speed {metrics.max_horizontal_speed_m_s:.2f} m/s, "
        f"max vertical speed {metrics.max_vertical_speed_m_s:.2f} m/s, "
        f"and altitude gain {metrics.max_altitude_gain_m:.2f} m. "
        f"Based on deterministic rules, {verdict}. "
        "Provide an API key to replace this fallback with an actual LLM-generated narrative."
    )


def build_insight(report: FlightReport) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key or OpenAI is None:
        return _rule_based_summary(report)

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    metrics = report.metrics
    prompt = dedent(
        f"""
        Summarize this UAV flight in 4-5 sentences and highlight anomalies or risky manoeuvres.
        Duration: {metrics.total_duration_s:.2f} s
        Distance: {metrics.total_distance_m:.2f} m
        Max horizontal speed from GPS: {metrics.max_horizontal_speed_m_s:.2f} m/s
        Max vertical speed from GPS: {metrics.max_vertical_speed_m_s:.2f} m/s
        Max horizontal speed from IMU integration: {metrics.max_horizontal_speed_imu_m_s:.2f} m/s
        Max vertical speed from IMU integration: {metrics.max_vertical_speed_imu_m_s:.2f} m/s
        Max acceleration: {metrics.max_acceleration_m_s2:.2f} m/s^2
        Max altitude gain: {metrics.max_altitude_gain_m:.2f} m
        """
    ).strip()

    try:
        response = client.responses.create(model=model, input=prompt)
        return response.output_text.strip()
    except Exception as exc:  # pragma: no cover
        return f"{_rule_based_summary(report)} LLM request failed: {exc}."
