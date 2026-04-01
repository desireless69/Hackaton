from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from telemetry_dashboard.analysis import analyze_flight
from telemetry_dashboard.parser import parse_bin_log


def main() -> None:
    logs = sorted((PROJECT_ROOT.parent / "bin").glob("*.BIN"))
    for log_path in logs:
        parsed = parse_bin_log(log_path)
        report = analyze_flight(parsed)
        metrics = report.metrics
        print(f"=== {log_path.name} ===")
        print(f"GPS frequency: {parsed.metadata.gps_frequency_hz:.2f} Hz")
        print(f"IMU frequency: {parsed.metadata.imu_frequency_hz:.2f} Hz")
        print(f"Duration: {metrics.total_duration_s:.2f} s")
        print(f"Distance: {metrics.total_distance_m:.2f} m")
        print(f"Max horizontal speed (GPS): {metrics.max_horizontal_speed_m_s:.2f} m/s")
        print(f"Max vertical speed (GPS): {metrics.max_vertical_speed_m_s:.2f} m/s")
        print(f"Max horizontal speed (IMU): {metrics.max_horizontal_speed_imu_m_s:.2f} m/s")
        print(f"Max vertical speed (IMU): {metrics.max_vertical_speed_imu_m_s:.2f} m/s")
        print(f"Max acceleration: {metrics.max_acceleration_m_s2:.2f} m/s^2")
        print(f"Max altitude gain: {metrics.max_altitude_gain_m:.2f} m")
        print()


if __name__ == "__main__":
    main()
