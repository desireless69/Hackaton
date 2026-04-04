from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def _sample_for_plotting(samples: pd.DataFrame) -> pd.DataFrame:
    step = max(len(samples) // 1200, 1)
    return samples.iloc[::step].copy()


def _center_lat_lon(samples: pd.DataFrame) -> tuple[float, float]:
    return float(samples["Lat"].mean()), float(samples["Lng"].mean())


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
                "colorbar": {
                    "title": color_title,
                    "x": 1.02,
                    "xanchor": "left",
                    "thickness": 16,
                    "len": 0.82,
                    "y": 0.5,
                },
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
            mode="markers",
            marker={"size": 8, "color": "#22c55e", "symbol": "diamond"},
            hovertemplate="Start point<extra></extra>",
            name="Start",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[north.iloc[-1]],
            y=[east.iloc[-1]],
            z=[height.iloc[-1]],
            mode="markers",
            marker={"size": 8, "color": "#ef4444", "symbol": "diamond"},
            hovertemplate="Finish point<extra></extra>",
            name="Finish",
        )
    )
    figure.update_layout(
        title="3D ENU trajectory colored by time",
        paper_bgcolor="#ffffff",
        font={"color": "#0f172a"},
        scene={
            "aspectmode": "manual",
            "aspectratio": aspect_ratio,
            "xaxis_title": "North (m)",
            "yaxis_title": "East (m)",
            "zaxis_title": "Height (m)",
            "xaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(226,232,240,0.92)",
                "gridcolor": "rgba(71,85,105,0.38)",
                "zerolinecolor": "rgba(51,65,85,0.48)",
                "linecolor": "rgba(51,65,85,0.72)",
                "color": "#334155",
            },
            "yaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(226,232,240,0.92)",
                "gridcolor": "rgba(71,85,105,0.38)",
                "zerolinecolor": "rgba(51,65,85,0.48)",
                "linecolor": "rgba(51,65,85,0.72)",
                "color": "#334155",
            },
            "zaxis": {
                "showbackground": True,
                "backgroundcolor": "rgba(226,232,240,0.92)",
                "gridcolor": "rgba(71,85,105,0.38)",
                "zerolinecolor": "rgba(51,65,85,0.48)",
                "linecolor": "rgba(51,65,85,0.72)",
                "color": "#334155",
            },
            "camera": {"eye": {"x": 1.9, "y": 1.9, "z": 1.25}},
            "bgcolor": "#ffffff",
        },
        margin={"l": 0, "r": 30, "t": 56, "b": 24},
        legend={
            "orientation": "h",
            "x": 0.0,
            "xanchor": "left",
            "y": -0.06,
            "yanchor": "top",
        },
        uirevision="trajectory-static",
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


def build_map_figure(samples: pd.DataFrame) -> go.Figure:
    figure_samples = _sample_for_plotting(samples)
    center_lat, center_lon = _center_lat_lon(figure_samples)

    figure = go.Figure(
        data=[
            go.Scattermap(
                lat=figure_samples["Lat"],
                lon=figure_samples["Lng"],
                mode="lines+markers",
                line={"width": 4, "color": "#0f766e"},
                marker={
                    "size": 8,
                    "color": figure_samples["TimeSec"],
                    "colorscale": "Turbo",
                    "showscale": True,
                    "colorbar": {"title": "Time (s)", "x": 1.02, "xanchor": "left"},
                },
                customdata=figure_samples[["Alt", "Spd", "TimeSec"]].to_numpy(),
                hovertemplate=(
                    "Time: %{customdata[2]:.2f} s<br>"
                    "Lat: %{lat:.6f}<br>"
                    "Lon: %{lon:.6f}<br>"
                    "Altitude: %{customdata[0]:.2f} m<br>"
                    "GPS speed: %{customdata[1]:.2f} m/s<extra></extra>"
                ),
                name="GPS route",
            )
        ]
    )
    figure.update_layout(
        title="Map view",
        height=520,
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
        map={
            "style": "open-street-map",
            "center": {"lat": center_lat, "lon": center_lon},
            "zoom": 15,
        },
        paper_bgcolor="#ffffff",
        font={"color": "#0f172a"},
    )
    return figure


def build_comparison_map_figure(
    samples_a: pd.DataFrame,
    samples_b: pd.DataFrame,
    label_a: str,
    label_b: str,
) -> go.Figure:
    figure_a = _sample_for_plotting(samples_a)
    figure_b = _sample_for_plotting(samples_b)
    combined = pd.concat([figure_a[["Lat", "Lng"]], figure_b[["Lat", "Lng"]]], ignore_index=True)
    center_lat, center_lon = _center_lat_lon(combined)

    figure = go.Figure()
    figure.add_trace(
        go.Scattermap(
            lat=figure_a["Lat"],
            lon=figure_a["Lng"],
            mode="lines+markers",
            line={"width": 4, "color": "#0f766e"},
            marker={"size": 7, "color": "#14b8a6"},
            customdata=figure_a[["Alt", "Spd", "TimeSec"]].to_numpy(),
            hovertemplate=(
                f"{label_a}<br>"
                "Time: %{customdata[2]:.2f} s<br>"
                "Altitude: %{customdata[0]:.2f} m<br>"
                "GPS speed: %{customdata[1]:.2f} m/s<extra></extra>"
            ),
            name=label_a,
        )
    )
    figure.add_trace(
        go.Scattermap(
            lat=figure_b["Lat"],
            lon=figure_b["Lng"],
            mode="lines+markers",
            line={"width": 4, "color": "#f97316"},
            marker={"size": 7, "color": "#fb923c"},
            customdata=figure_b[["Alt", "Spd", "TimeSec"]].to_numpy(),
            hovertemplate=(
                f"{label_b}<br>"
                "Time: %{customdata[2]:.2f} s<br>"
                "Altitude: %{customdata[0]:.2f} m<br>"
                "GPS speed: %{customdata[1]:.2f} m/s<extra></extra>"
            ),
            name=label_b,
        )
    )
    figure.update_layout(
        title="Route comparison map",
        height=560,
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
        map={
            "style": "open-street-map",
            "center": {"lat": center_lat, "lon": center_lon},
            "zoom": 14,
        },
        paper_bgcolor="#ffffff",
        font={"color": "#0f172a"},
        legend={"orientation": "h", "x": 0, "y": 1.02, "xanchor": "left", "yanchor": "bottom"},
    )
    return figure
