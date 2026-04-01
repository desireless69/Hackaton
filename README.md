# Hackaton

## Overview

This project is an ArduPilot telemetry analyzer that:

- parses `.BIN` logs and extracts GPS, IMU, and ATT messages;
- estimates sensor sampling frequencies and tracks units;
- computes total duration, distance via the Haversine formula, altitude gain, GPS peak speeds, and IMU-derived speeds via trapezoidal integration;
- converts WGS-84 coordinates into a local ENU frame;
- shows the flight through a Streamlit dashboard with a 3D view and 2D fallback projections;
- can optionally generate a short LLM-based flight insight.

## Structure

```text
.
|-- app.py
|-- run_analysis.py
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yaml
|-- src/telemetry_dashboard
|-- bin
`-- README.md
```

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

## Console validation

```bash
python run_analysis.py
```

## Docker run

```bash
docker compose up --build
```

## Notes

- Distance is computed from valid GPS fixes with the Haversine formula.
- IMU accelerations are rotated into ENU using ATT roll, pitch, and yaw.
- Speed from IMU is recovered with trapezoidal integration, but GPS peak speed is kept as the headline metric because pure IMU integration drifts.
- The dashboard shows both 3D and 2D trajectory views to stay readable even when WebGL rendering is limited.
