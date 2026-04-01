from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_trajectory_figure(samples: pd.DataFrame):
    figure_samples = samples.iloc[:: max(len(samples) // 1200, 1)].copy()
    hover_template = (
        "Time: %{customdata[0]:.2f} s<br>"
        "Horizontal speed: %{customdata[1]:.2f} m/s<br>"
        "Vertical speed: %{customdata[2]:.2f} m/s<br>"
        "East: %{x:.2f} m<br>"
        "North: %{y:.2f} m<br>"
        "Up: %{z:.2f} m<extra></extra>"
    )

    figure = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "scene", "colspan": 2}, None],
            [{"type": "xy"}, {"type": "xy"}],
        ],
        row_heights=[0.72, 0.28],
        column_widths=[0.5, 0.5],
        subplot_titles=("3D trajectory", "Top view: East vs North", "Altitude profile: Time vs Up"),
    )
    figure.add_trace(
        go.Scatter3d(
            x=figure_samples["X_ENU"],
            y=figure_samples["Y_ENU"],
            z=figure_samples["Z_ENU"],
            mode="lines",
            line={"color": "#22d3ee", "width": 10},
            name="Trajectory",
            hoverinfo="skip",
        )
        ,
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter3d(
            x=figure_samples["X_ENU"],
            y=figure_samples["Y_ENU"],
            z=figure_samples["Z_ENU"],
            mode="markers",
            marker={
                "size": 5,
                "color": figure_samples["TimeSec"],
                "colorscale": "Turbo",
                "colorbar": {"title": "Time (s)"},
                "opacity": 0.95,
            },
            customdata=figure_samples[["TimeSec", "HorizontalSpeed", "VerticalSpeed"]].to_numpy(),
            hovertemplate=hover_template,
            name="Samples",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter3d(
            x=[figure_samples["X_ENU"].iloc[0]],
            y=[figure_samples["Y_ENU"].iloc[0]],
            z=[figure_samples["Z_ENU"].iloc[0]],
            mode="markers+text",
            marker={"size": 8, "color": "#22c55e", "symbol": "diamond"},
            text=["Start"],
            textposition="top center",
            name="Start",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter3d(
            x=[figure_samples["X_ENU"].iloc[-1]],
            y=[figure_samples["Y_ENU"].iloc[-1]],
            z=[figure_samples["Z_ENU"].iloc[-1]],
            mode="markers+text",
            marker={"size": 8, "color": "#ef4444", "symbol": "diamond"},
            text=["Finish"],
            textposition="top center",
            name="Finish",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=figure_samples["X_ENU"],
            y=figure_samples["Y_ENU"],
            mode="lines+markers",
            line={"color": "#22d3ee", "width": 3},
            marker={
                "size": 5,
                "color": figure_samples["TimeSec"],
                "colorscale": "Turbo",
                "showscale": False,
            },
            name="Top view",
            hovertemplate="East: %{x:.2f} m<br>North: %{y:.2f} m<extra></extra>",
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=figure_samples["TimeSec"],
            y=figure_samples["Z_ENU"],
            mode="lines",
            line={"color": "#f59e0b", "width": 3},
            name="Altitude profile",
            hovertemplate="Time: %{x:.2f} s<br>Up: %{y:.2f} m<extra></extra>",
        ),
        row=2,
        col=2,
    )
    figure.update_layout(
        title="Flight trajectory in ENU coordinates",
        scene={
            "aspectmode": "data",
            "xaxis_title": "East (m)",
            "yaxis_title": "North (m)",
            "zaxis_title": "Up (m)",
            "camera": {
                "eye": {"x": 1.6, "y": 1.4, "z": 1.2},
            },
            "bgcolor": "rgba(0,0,0,0)",
        },
        xaxis={"title": "East (m)", "zeroline": False},
        yaxis={"title": "North (m)", "zeroline": False},
        xaxis2={"title": "Time (s)", "zeroline": False},
        yaxis2={"title": "Up (m)", "zeroline": False},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        legend={"orientation": "h"},
        height=900,
    )
    return figure
