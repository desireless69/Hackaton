from __future__ import annotations

from pathlib import Path

import pandas as pd
from pymavlink import mavutil

from telemetry_dashboard.models import ParsedFlight, SensorMetadata

GPS_FIELDS = ("TimeUS", "Status", "Lat", "Lng", "Alt", "Spd", "VZ", "NSats", "HDop")
IMU_FIELDS = ("TimeUS", "AccX", "AccY", "AccZ", "GyrX", "GyrY", "GyrZ")
ATT_FIELDS = ("TimeUS", "Roll", "Pitch", "Yaw")


def _sampling_frequency_hz(samples: pd.DataFrame) -> float:
    if len(samples) < 2:
        return 0.0

    deltas = samples["TimeUS"].sort_values().diff().dropna() / 1_000_000
    median_dt = deltas.median()
    if not median_dt or median_dt <= 0:
        return 0.0
    return float(1.0 / median_dt)


def _records_to_frame(records: list[dict], required_fields: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        missing = {field: pd.Series(dtype="float64") for field in required_fields}
        return pd.DataFrame(missing)
    return frame[list(required_fields)].sort_values("TimeUS").drop_duplicates("TimeUS").reset_index(drop=True)


def parse_bin_log(log_path: str | Path) -> ParsedFlight:
    resolved_path = Path(log_path).resolve()
    mav_log = mavutil.mavlink_connection(str(resolved_path))

    gps_records: list[dict] = []
    imu_records: list[dict] = []
    att_records: list[dict] = []

    while True:
        message = mav_log.recv_match(type=["GPS", "IMU", "ATT"], blocking=False)
        if message is None:
            break

        payload = message.to_dict()
        message_type = message.get_type()

        if message_type == "GPS":
            gps_records.append({field: payload[field] for field in GPS_FIELDS})
        elif message_type == "IMU":
            imu_records.append({field: payload[field] for field in IMU_FIELDS})
        elif message_type == "ATT":
            att_records.append({field: payload[field] for field in ATT_FIELDS})

    gps_frame = _records_to_frame(gps_records, GPS_FIELDS)
    imu_frame = _records_to_frame(imu_records, IMU_FIELDS)
    att_frame = _records_to_frame(att_records, ATT_FIELDS)

    if gps_frame.empty or imu_frame.empty:
        raise ValueError(f"Could not extract both GPS and IMU telemetry from {resolved_path.name}.")

    valid_gps = gps_frame[gps_frame["Status"] >= 3].copy()
    if valid_gps.empty:
        valid_gps = gps_frame.copy()

    imu_with_attitude = pd.merge_asof(
        imu_frame,
        att_frame,
        on="TimeUS",
        direction="nearest",
        tolerance=100_000,
    ).dropna(subset=["Roll", "Pitch", "Yaw"])

    merged_samples = pd.merge_asof(
        imu_with_attitude,
        valid_gps,
        on="TimeUS",
        direction="nearest",
        tolerance=250_000,
    ).dropna(subset=["Lat", "Lng", "Alt"])

    if merged_samples.empty:
        raise ValueError(f"Could not align IMU/ATT samples with valid GPS fixes for {resolved_path.name}.")

    merged_samples["TimeSec"] = (
        merged_samples["TimeUS"] - float(merged_samples["TimeUS"].iloc[0])
    ) / 1_000_000

    metadata = SensorMetadata(
        gps_frequency_hz=_sampling_frequency_hz(valid_gps),
        imu_frequency_hz=_sampling_frequency_hz(imu_frame),
        gps_rows=len(valid_gps),
        imu_rows=len(imu_frame),
        gps_units={
            "Lat": "degrees",
            "Lng": "degrees",
            "Alt": "meters",
            "Spd": "m/s",
            "VZ": "m/s",
        },
        imu_units={
            "AccX": "m/s^2",
            "AccY": "m/s^2",
            "AccZ": "m/s^2",
            "GyrX": "rad/s",
            "GyrY": "rad/s",
            "GyrZ": "rad/s",
        },
    )

    return ParsedFlight(
        log_path=str(resolved_path),
        gps_samples=valid_gps.reset_index(drop=True),
        imu_samples=imu_frame.reset_index(drop=True),
        merged_samples=merged_samples.reset_index(drop=True),
        metadata=metadata,
    )
