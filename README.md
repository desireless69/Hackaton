# Hackaton

## Overview

This project is an ArduPilot telemetry analyzer that:

- parses `.BIN` logs and extracts GPS, IMU, and ATT messages;
- estimates sensor sampling frequencies and tracks units;
- computes total duration, distance via the Haversine formula, altitude gain, GPS peak speeds, and IMU-derived speeds via trapezoidal integration;
- converts WGS-84 coordinates into a local ENU frame;
- serves a FastAPI web app with one main 3D ENU trajectory view plus supplementary 2D projections;
- generates an AI flight conclusion through Gemini when `GEMINI_API_KEY` is available.

## Structure

```text
.
|-- main.py
|-- requirements.txt
|-- Dockerfile
|-- docker-compose.yaml
|-- src/telemetry_dashboard
|-- src/static
|-- src/templates
|-- bin
`-- README.md
```

## Local run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000`.

## Gemini setup

Create a local `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

## Docker run

```bash
docker compose up --build
```

## Notes

- Distance is computed from valid GPS fixes with the Haversine formula.
- IMU accelerations are rotated into ENU using ATT roll, pitch, and yaw.
- Speed from IMU is recovered with trapezoidal integration, but GPS peak speed is kept as the headline metric because pure IMU integration drifts.
- The main 3D plot uses `X = North`, `Y = East`, `Z = Height` and dynamic coloring by time.
