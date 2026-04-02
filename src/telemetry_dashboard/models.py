from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class SensorMetadata:
    gps_frequency_hz: float
    imu_frequency_hz: float
    gps_rows: int
    imu_rows: int
    gps_units: dict[str, str]
    imu_units: dict[str, str]


@dataclass(slots=True)
class ParsedFlight:
    log_path: str
    gps_samples: pd.DataFrame
    imu_samples: pd.DataFrame
    merged_samples: pd.DataFrame
    metadata: SensorMetadata


@dataclass(slots=True)
class FlightMetrics:
    total_duration_s: float
    total_distance_m: float
    max_horizontal_speed_m_s: float
    max_vertical_speed_m_s: float
    max_horizontal_speed_imu_m_s: float
    max_vertical_speed_imu_m_s: float
    max_acceleration_m_s2: float
    max_altitude_gain_m: float

    def as_dict(self) -> dict[str, float]:
        return {
            "total_duration_s": self.total_duration_s,
            "total_distance_m": self.total_distance_m,
            "max_horizontal_speed_m_s": self.max_horizontal_speed_m_s,
            "max_vertical_speed_m_s": self.max_vertical_speed_m_s,
            "max_horizontal_speed_imu_m_s": self.max_horizontal_speed_imu_m_s,
            "max_vertical_speed_imu_m_s": self.max_vertical_speed_imu_m_s,
            "max_acceleration_m_s2": self.max_acceleration_m_s2,
            "max_altitude_gain_m": self.max_altitude_gain_m,
        }


@dataclass(slots=True)
class FlightReport:
    parsed_flight: ParsedFlight
    enriched_samples: pd.DataFrame
    metrics: FlightMetrics
