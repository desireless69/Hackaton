from __future__ import annotations

import math

import numpy as np
import pandas as pd

from telemetry_dashboard.models import FlightMetrics, FlightReport, ParsedFlight

EARTH_RADIUS_M = 6_378_137.0
GRAVITY_M_S2 = 9.80665


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * 6_371_000.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _body_to_enu_matrix(roll_deg: float, pitch_deg: float, yaw_deg: float) -> np.ndarray:
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rotation_body_to_ned = np.array(
        [
            [cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
            [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
            [-sp, sr * cp, cr * cp],
        ]
    )

    ned_to_enu = np.array(
        [
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0],
        ]
    )
    return ned_to_enu @ rotation_body_to_ned


def _integrate_trapezoidal(acceleration: pd.Series, dt: pd.Series) -> np.ndarray:
    integrated = np.zeros(len(acceleration))
    for idx in range(1, len(acceleration)):
        integrated[idx] = integrated[idx - 1] + 0.5 * (
            acceleration.iloc[idx] + acceleration.iloc[idx - 1]
        ) * dt.iloc[idx]
    return integrated


def _wgs84_to_enu(samples: pd.DataFrame) -> pd.DataFrame:
    first_lat = math.radians(samples["Lat"].iloc[0])
    first_alt = float(samples["Alt"].iloc[0])

    delta_lat = np.radians(samples["Lat"].to_numpy()) - first_lat
    delta_lon = np.radians(samples["Lng"].to_numpy()) - math.radians(samples["Lng"].iloc[0])

    samples["X_ENU"] = delta_lon * EARTH_RADIUS_M * math.cos(first_lat)
    samples["Y_ENU"] = delta_lat * EARTH_RADIUS_M
    samples["Z_ENU"] = samples["Alt"] - first_alt
    return samples


def _total_distance_m(gps_samples: pd.DataFrame) -> float:
    points = gps_samples[["Lat", "Lng"]].drop_duplicates().reset_index(drop=True)
    distance = 0.0
    for idx in range(1, len(points)):
        previous = points.iloc[idx - 1]
        current = points.iloc[idx]
        distance += haversine_distance_m(previous["Lat"], previous["Lng"], current["Lat"], current["Lng"])
    return distance


def analyze_flight(parsed_flight: ParsedFlight) -> FlightReport:
    samples = parsed_flight.merged_samples.copy()
    samples = _wgs84_to_enu(samples)

    samples["dt"] = samples["TimeSec"].diff().fillna(0.0).clip(lower=0.0)

    acceleration_enu = []
    for row in samples.itertuples():
        rotation = _body_to_enu_matrix(row.Roll, row.Pitch, row.Yaw)
        body_acc = np.array([row.AccX, row.AccY, row.AccZ])
        world_acc = rotation @ body_acc
        world_acc[2] -= GRAVITY_M_S2
        acceleration_enu.append(world_acc)

    acceleration_enu = np.vstack(acceleration_enu)
    samples["AccEast"] = acceleration_enu[:, 0]
    samples["AccNorth"] = acceleration_enu[:, 1]
    samples["AccUp"] = acceleration_enu[:, 2]
    samples["AccHorizontal"] = np.sqrt(samples["AccEast"] ** 2 + samples["AccNorth"] ** 2)
    samples["AccMagnitude"] = np.sqrt(
        samples["AccEast"] ** 2 + samples["AccNorth"] ** 2 + samples["AccUp"] ** 2
    )

    samples["VelEast"] = _integrate_trapezoidal(samples["AccEast"], samples["dt"])
    samples["VelNorth"] = _integrate_trapezoidal(samples["AccNorth"], samples["dt"])
    samples["VelUp"] = _integrate_trapezoidal(samples["AccUp"], samples["dt"])
    samples["HorizontalSpeed"] = np.sqrt(samples["VelEast"] ** 2 + samples["VelNorth"] ** 2)
    samples["VerticalSpeed"] = samples["VelUp"].abs()

    metrics = FlightMetrics(
        total_duration_s=float(samples["TimeSec"].iloc[-1]),
        total_distance_m=float(_total_distance_m(parsed_flight.gps_samples)),
        max_horizontal_speed_m_s=float(parsed_flight.gps_samples["Spd"].max()),
        max_vertical_speed_m_s=float(parsed_flight.gps_samples["VZ"].abs().max()),
        max_horizontal_speed_imu_m_s=float(samples["HorizontalSpeed"].max()),
        max_vertical_speed_imu_m_s=float(samples["VerticalSpeed"].max()),
        max_acceleration_m_s2=float(samples["AccMagnitude"].max()),
        max_altitude_gain_m=float(parsed_flight.gps_samples["Alt"].max() - parsed_flight.gps_samples["Alt"].min()),
    )

    return FlightReport(
        parsed_flight=parsed_flight,
        enriched_samples=samples,
        metrics=metrics,
    )
