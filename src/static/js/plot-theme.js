function getPlotTheme(theme) {
    const isDark = theme === "dark";
    return {
        paper_bgcolor: isDark ? "#0a1421" : "#ffffff",
        plot_bgcolor: isDark ? "#0f1b2b" : "#eef5fb",
        font: { color: isDark ? "#edf6ff" : "#112033" },
        legend: { font: { color: isDark ? "#edf6ff" : "#112033" } },
        title: { font: { color: isDark ? "#edf6ff" : "#112033" } },
        xaxis: {
            color: isDark ? "#c7d2e0" : "#405165",
            gridcolor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(64, 81, 101, 0.16)",
            zerolinecolor: isDark ? "rgba(148, 163, 184, 0.24)" : "rgba(64, 81, 101, 0.22)",
        },
        yaxis: {
            color: isDark ? "#c7d2e0" : "#405165",
            gridcolor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(64, 81, 101, 0.16)",
            zerolinecolor: isDark ? "rgba(148, 163, 184, 0.24)" : "rgba(64, 81, 101, 0.22)",
        },
        scene: {
            bgcolor: isDark ? "#0a1421" : "#ffffff",
            xaxis: {
                color: isDark ? "#c7d2e0" : "#405165",
                backgroundcolor: isDark ? "#0f1b2b" : "#eef5fb",
                gridcolor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(64, 81, 101, 0.16)",
                zerolinecolor: isDark ? "rgba(148, 163, 184, 0.24)" : "rgba(64, 81, 101, 0.22)",
            },
            yaxis: {
                color: isDark ? "#c7d2e0" : "#405165",
                backgroundcolor: isDark ? "#0f1b2b" : "#eef5fb",
                gridcolor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(64, 81, 101, 0.16)",
                zerolinecolor: isDark ? "rgba(148, 163, 184, 0.24)" : "rgba(64, 81, 101, 0.22)",
            },
            zaxis: {
                color: isDark ? "#c7d2e0" : "#405165",
                backgroundcolor: isDark ? "#0f1b2b" : "#eef5fb",
                gridcolor: isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(64, 81, 101, 0.16)",
                zerolinecolor: isDark ? "rgba(148, 163, 184, 0.24)" : "rgba(64, 81, 101, 0.22)",
            },
        },
    };
}

function restylePlots(theme) {
    if (!window.Plotly) {
        window.setTimeout(() => restylePlots(theme), 120);
        return;
    }

    document.querySelectorAll(".js-plotly-plot").forEach((plot) => {
        window.Plotly.relayout(plot, getPlotTheme(theme));
    });
}

document.addEventListener("DOMContentLoaded", () => {
    restylePlots(document.documentElement.getAttribute("data-theme") || "light");
});

document.addEventListener("telemetry:theme-change", (event) => {
    restylePlots(event.detail.theme);
});
