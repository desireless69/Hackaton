from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def _sample_for_plotting(samples: pd.DataFrame) -> pd.DataFrame:
    step = max(len(samples) // 1200, 1)
    return samples.iloc[::step].copy()


def build_trajectory_figure(samples: pd.DataFrame) -> go.Figure:
    figure_samples = _sample_for_plotting(samples)
    color_column = "TimeSec"
    color_title = "Time (s)"
    colorscale = "Turbo"
    north = figure_samples["Y_ENU"]
    east = figure_samples["X_ENU"]
    height = figure_samples["Z_ENU"]

    north_span = max(float(north.max() - north.min()), 1.0)
    east_span = max(float(east.max() - east.min()), 1.0)
    height_span = max(float(height.max() - height.min()), 1.0)
    max_span = max(north_span, east_span, height_span)
    aspect_ratio = {
        "x": max(north_span / max_span, 0.35),
        "y": max(east_span / max_span, 0.35),
        "z": max(height_span / max_span, 0.35),
    }

    hover_template = (
        "Time: %{customdata[0]:.2f} s<br>"
        "Horizontal speed: %{customdata[1]:.2f} m/s<br>"
        "Vertical speed: %{customdata[2]:.2f} m/s<br>"
        "North: %{x:.2f} m<br>"
        "East: %{y:.2f} m<br>"
        "Height: %{z:.2f} m<extra></extra>"
    )

    figure = go.Figure()
    figure.add_trace(
        go.Scatter3d(
            x=north,
            y=east,
            z=height,
            mode="lines",
            line={"color": "rgba(148, 163, 184, 0.45)", "width": 8},
            name="Path",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=north,
            y=east,
            z=height,
            mode="markers",
            marker={
                "size": 6,
                "color": figure_samples[color_column],
                "colorscale": colorscale,
                "colorbar": {"title": color_title},
                "opacity": 0.95,
            },
            customdata=figure_samples[["TimeSec", "HorizontalSpeed", "VerticalSpeed"]].to_numpy(),
            hovertemplate=hover_template,
            name="Trajectory samples",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[north.iloc[0]],
            y=[east.iloc[0]],
            z=[height.iloc[0]],
            mode="markers+text",
            marker={"size": 8, "color": "#22c55e", "symbol": "diamond"},
            text=["Start"],
            textposition="top center",
            name="Start",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[north.iloc[-1]],
            y=[east.iloc[-1]],
            z=[height.iloc[-1]],
            mode="markers+text",
            marker={"size": 8, "color": "#ef4444", "symbol": "diamond"},
            text=["Finish"],
            textposition="top center",
            name="Finish",
        )
    )
    figure.update_layout(
        title="3D ENU trajectory colored by time",
        scene={
            "aspectmode": "manual",
            "aspectratio": aspect_ratio,
            "xaxis_title": "North (m)",
            "yaxis_title": "East (m)",
            "zaxis_title": "Height (m)",
            "xaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(15,23,42,0.18)",
                "gridcolor": "rgba(148,163,184,0.18)",
            },
            "yaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(15,23,42,0.18)",
                "gridcolor": "rgba(148,163,184,0.18)",
            },
            "zaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(15,23,42,0.18)",
                "gridcolor": "rgba(148,163,184,0.18)",
            },
            "camera": {"eye": {"x": 1.9, "y": 1.9, "z": 1.25}},
            "bgcolor": "rgba(0,0,0,0)",
        },
        margin={"l": 0, "r": 0, "t": 56, "b": 0},
        legend={"orientation": "h"},
        height=760,
    )
    return figure


def build_projection_figures(samples: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    figure_samples = _sample_for_plotting(samples)

    top_view = go.Figure(
        data=[
            go.Scatter(
                x=figure_samples["Y_ENU"],
                y=figure_samples["X_ENU"],
                mode="lines+markers",
                line={"color": "#22d3ee", "width": 3},
                marker={
                    "size": 5,
                    "color": figure_samples["TimeSec"],
                    "colorscale": "Turbo",
                    "showscale": False,
                },
                hovertemplate="North: %{x:.2f} m<br>East: %{y:.2f} m<extra></extra>",
                name="Top view",
            )
        ]
    )
    top_view.update_layout(
        title="Top view (North vs East)",
        xaxis_title="North (m)",
        yaxis_title="East (m)",
        height=320,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )

    altitude_profile = go.Figure(
        data=[
            go.Scatter(
                x=figure_samples["TimeSec"],
                y=figure_samples["Z_ENU"],
                mode="lines",
                line={"color": "#f59e0b", "width": 3},
                hovertemplate="Time: %{x:.2f} s<br>Up: %{y:.2f} m<extra></extra>",
                name="Altitude profile",
            )
        ]
    )
    altitude_profile.update_layout(
        title="Altitude profile (Time vs Height)",
        xaxis_title="Time (s)",
        yaxis_title="Height (m)",
        height=320,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )

    return top_view, altitude_profile
