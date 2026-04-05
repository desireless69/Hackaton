# React Frontend

This folder contains a separate React + Vite frontend for the telemetry dashboard.

## Run

```bash
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies backend requests to the FastAPI app on `http://127.0.0.1:8000`.

## Notes

- The current FastAPI templates still work as before.
- This React app is a clean frontend workspace so you can start moving UI into components gradually.
- Proxy targets already include `/health`, `/analyze`, `/compare`, and `/reports`.
