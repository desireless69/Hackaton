from __future__ import annotations

import pandas as pd
import plotly.express as px


def build_trajectory_figure(samples: pd.DataFrame):
    figure_samples = samples.iloc[:: max(len(samples) // 1200, 1)].copy()

    figure = px.line_3d(
        figure_samples,
        x="X_ENU",
        y="Y_ENU",
        z="Z_ENU",
        color="TimeSec",
        hover_data={
            "TimeSec": ":.2f",
            "HorizontalSpeed": ":.2f",
            "VerticalSpeed": ":.2f",
            "Z_ENU": ":.2f",
        },
        labels={
            "X_ENU": "East (m)",
            "Y_ENU": "North (m)",
            "Z_ENU": "Up (m)",
            "TimeSec": "Time (s)",
        },
        title="3D trajectory in the local ENU frame",
    )
    figure.update_traces(line={"width": 5})
    figure.update_layout(scene={"aspectmode": "data"})
    return figure
