from __future__ import annotations

import json
import os
import re
from textwrap import dedent
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from telemetry_dashboard.models import FlightReport

SECTION_HEADERS = (
    "Overall assessment",
    "Key metrics",
    "Anomalies or risks",
    "Sensor confidence",
)


def _rule_based_summary(report: FlightReport) -> str:
    metrics = report.metrics
    drift_note = (
        "IMU and GPS speed estimates are reasonably close."
        if abs(metrics.max_horizontal_speed_m_s - metrics.max_horizontal_speed_imu_m_s) < 8
        else "The IMU and GPS speed peaks differ noticeably, which suggests IMU integration drift."
    )
    risk_note = "No critical anomalies stand out."
    if metrics.max_vertical_speed_m_s > 80:
        risk_note = "The flight shows very aggressive vertical motion and deserves a safety review."
    elif metrics.max_horizontal_speed_m_s > 45:
        risk_note = "The flight reached a high horizontal speed envelope."

    return dedent(
        f"""
        ### Overall assessment
        The UAV completed a dynamic flight that covered {metrics.total_distance_m:.2f} m in {metrics.total_duration_s:.2f} s.

        ### Key metrics
        Peak horizontal speed reached {metrics.max_horizontal_speed_m_s:.2f} m/s, peak vertical speed reached {metrics.max_vertical_speed_m_s:.2f} m/s, and altitude gain was {metrics.max_altitude_gain_m:.2f} m.

        ### Anomalies or risks
        {risk_note} Maximum measured acceleration was {metrics.max_acceleration_m_s2:.2f} m/s^2.

        ### Sensor confidence
        {drift_note}
        """
    ).strip()


def _prompt_from_report(report: FlightReport) -> str:
    metrics = report.metrics
    return dedent(
        f"""
        You are analyzing a UAV flight log.

        Return Markdown only using exactly these section headers:
        ### Overall assessment
        ### Key metrics
        ### Anomalies or risks
        ### Sensor confidence

        Requirements:
        - Write exactly 4 sections and keep the section titles exactly as provided.
        - Write 1-2 short sentences in each section.
        - Mention the actual numeric values.
        - Explicitly mention sudden altitude loss, high vertical speed, overspeed, or high acceleration when they appear.
        - If IMU and GPS speeds differ strongly, explicitly say this suggests IMU drift.
        - Do not add any extra headers or intro text.
        - Do not use code fences.
        - Do not collapse the answer into one paragraph.

        Flight data:
        - Duration: {metrics.total_duration_s:.2f} s
        - Distance: {metrics.total_distance_m:.2f} m
        - Max horizontal speed from GPS: {metrics.max_horizontal_speed_m_s:.2f} m/s
        - Max vertical speed from GPS: {metrics.max_vertical_speed_m_s:.2f} m/s
        - Max horizontal speed from IMU integration: {metrics.max_horizontal_speed_imu_m_s:.2f} m/s
        - Max vertical speed from IMU integration: {metrics.max_vertical_speed_imu_m_s:.2f} m/s
        - Max acceleration: {metrics.max_acceleration_m_s2:.2f} m/s^2
        - Max altitude gain: {metrics.max_altitude_gain_m:.2f} m
        """
    ).strip()


def _split_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", text, flags=re.MULTILINE))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[title] = body
    return sections


def _normalize_summary(text: str, report: FlightReport) -> str:
    fallback_sections = _split_sections(_rule_based_summary(report))
    model_sections = _split_sections(text)

    if not model_sections:
        model_sections = {"Overall assessment": text.strip()}

    normalized: list[str] = []
    for title in SECTION_HEADERS:
        body = model_sections.get(title) or fallback_sections.get(title, "")
        if not body:
            continue
        normalized.append(f"### {title}\n{body.strip()}")
    return "\n\n".join(normalized).strip()


def _gemini_summary(report: FlightReport, api_key: str, model: str) -> str:
    prompt = _prompt_from_report(report)
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "maxOutputTokens": 700,
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {details}") from exc
    except URLError as exc:  # pragma: no cover
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    candidates = body.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {body}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned an empty response: {body}")
    return _normalize_summary(text, report)


def build_insight(report: FlightReport) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if gemini_api_key:
        try:
            return _gemini_summary(report, gemini_api_key, gemini_model)
        except Exception:  # pragma: no cover
            return _rule_based_summary(report)

    return _rule_based_summary(report)
