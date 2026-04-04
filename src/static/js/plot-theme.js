function plotTheme(theme) {
    const dark = theme === "dark";
    const axisColor = dark ? "#cbd5e1" : "#334155";
    const gridColor = dark ? "rgba(148, 163, 184, 0.18)" : "rgba(71, 85, 105, 0.38)";
    const zeroColor = dark ? "rgba(148, 163, 184, 0.24)" : "rgba(51, 65, 85, 0.48)";
    const lineColor = dark ? "#cbd5e1" : "#334155";
    const paper = dark ? "#0f172a" : "#ffffff";
    const plot = dark ? "#111c31" : "#eef4fb";
    const sceneBackground = dark ? "rgba(15, 23, 42, 0.92)" : "rgba(226, 232, 240, 0.92)";

    return {
        paper_bgcolor: paper,
        plot_bgcolor: plot,
        font: { color: dark ? "#e2e8f0" : "#0f172a" },
        legend: { font: { color: dark ? "#e2e8f0" : "#0f172a" } },
        title: { font: { color: dark ? "#e2e8f0" : "#0f172a" } },
        xaxis: { color: axisColor, gridcolor: gridColor, zerolinecolor: zeroColor, linecolor: lineColor },
        yaxis: { color: axisColor, gridcolor: gridColor, zerolinecolor: zeroColor, linecolor: lineColor },
        scene: {
            xaxis: { color: axisColor, gridcolor: gridColor, zerolinecolor: zeroColor, linecolor: lineColor, backgroundcolor: sceneBackground },
            yaxis: { color: axisColor, gridcolor: gridColor, zerolinecolor: zeroColor, linecolor: lineColor, backgroundcolor: sceneBackground },
            zaxis: { color: axisColor, gridcolor: gridColor, zerolinecolor: zeroColor, linecolor: lineColor, backgroundcolor: sceneBackground },
            bgcolor: dark ? "#0f172a" : "#ffffff",
        },
    };
}

function restylePlots(theme) {
    if (!window.Plotly) {
        window.setTimeout(() => restylePlots(theme), 120);
        return;
    }
    document.querySelectorAll(".js-plotly-plot").forEach((plot) => {
        window.Plotly.relayout(plot, plotTheme(theme));
    });
}

document.addEventListener("DOMContentLoaded", () => {
    restylePlots(document.documentElement.getAttribute("data-theme") || "light");
});

document.addEventListener("telemetry:theme-change", (event) => {
    restylePlots(event.detail.theme);
});
