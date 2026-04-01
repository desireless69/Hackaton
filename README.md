<<<<<<< Updated upstream
# Hackaton
=======
# Hackaton

## Overview

This solution implements an ArduPilot telemetry analyzer that:

- parses raw `.BIN` logs and extracts GPS, IMU, and ATT messages;
- estimates sensor sampling frequencies and keeps units metadata;
- computes mission metrics, including total duration, distance via the Haversine formula, altitude gain, stable GPS-derived peak speeds, and IMU-based speed estimates obtained with trapezoidal integration;
- converts WGS-84 coordinates into a local ENU frame and renders an interactive 3D trajectory;
- exposes everything through a Streamlit web dashboard with optional LLM-generated flight insight.

## Why this stack

- `pymavlink` parses ArduPilot binary logs without a custom decoder.
- `pandas` and `numpy` keep the telemetry pipeline explicit and easy to validate.
- `plotly` gives an interactive 3D view with hover details and dynamic coloring.
- `streamlit` is the fastest clean path to a usable web dashboard.
- Docker makes the submission easy to verify on another machine.

## Project structure

```text
.
|-- backend
|   |-- app.py
|   |-- run_analysis.py
|   |-- requirements.txt
|   `-- src/telemetry_dashboard
|       |-- analysis.py
|       |-- llm_summary.py
|       |-- models.py
|       |-- parser.py
|       `-- visualization.py
|-- bin
|   |-- 00000001.BIN
|   `-- 00000019.BIN
`-- docker-compose.yaml
```

## Analytics notes

- Distance is computed only from valid GPS fixes using the Haversine formula, as required.
- IMU accelerations are rotated from the body frame into the ENU frame by using ATT roll, pitch, and yaw.
- The vertical ENU acceleration subtracts gravity before integration.
- Horizontal and vertical speeds are then recovered with trapezoidal integration.
- IMU integration always drifts over time, so the dashboard reports GPS-based peak speeds as the stable headline metrics and shows integrated IMU speeds as an algorithmic cross-check.

This is the key theoretical note for the demo: direct IMU integration is mandatory for the challenge and implemented here, but it accumulates bias and noise. GPS-derived velocity is less reactive but more stable over longer intervals, so showing both values makes the analysis more honest and useful.

## Local run

1. Install Python 3.12+.
2. Create and activate a virtual environment if you want an isolated setup.
3. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Start the dashboard:

```bash
streamlit run backend/app.py
```

5. Open `http://localhost:8501`.
6. Pick one of the bundled sample logs or upload another ArduPilot `.BIN` file.

## Headless validation

To print metrics for the bundled logs:

```bash
python backend/run_analysis.py
```

## Docker run

```bash
docker compose up --build
```

Then open `http://localhost:8501`.

## Optional AI assistant

If you want a real LLM-generated conclusion instead of the built-in deterministic fallback, set:

```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4.1-mini
```

The dashboard will then call the OpenAI Responses API and generate a short textual flight assessment.

## Files used for the challenge

The analyzer is validated against both provided logs:

- `bin/00000001.BIN`
- `bin/00000019.BIN`
>>>>>>> Stashed changes
