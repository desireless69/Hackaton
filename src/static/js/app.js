const UI_PRESETS = {
    "mission-control": {
        label: "Mission Control",
        description: "Balanced default for metrics, summaries, and charts.",
    },
    "field-ops": {
        label: "Field Ops",
        description: "Higher contrast look for live demos and quick scanning.",
    },
    blueprint: {
        label: "Blueprint",
        description: "Minimal neutral shell for building your own component system.",
    },
};

const STORAGE_KEYS = {
    theme: "telemetry-theme",
    preset: "telemetry-ui-preset",
    density: "telemetry-density",
};

const root = document.documentElement;

function getStoredTheme() {
    return localStorage.getItem(STORAGE_KEYS.theme) || root.getAttribute("data-theme") || "light";
}

function getStoredPreset() {
    return localStorage.getItem(STORAGE_KEYS.preset) || root.getAttribute("data-ui-preset") || "mission-control";
}

function getStoredDensity() {
    return localStorage.getItem(STORAGE_KEYS.density) || root.getAttribute("data-density") || "comfortable";
}

function updateThemeButton(button, theme) {
    if (!button) {
        return;
    }

    button.textContent = theme === "dark" ? "☀" : "☾";
    button.title = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
}

function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEYS.theme, theme);
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => updateThemeButton(button, theme));
    document.dispatchEvent(new CustomEvent("telemetry:theme-change", { detail: { theme } }));
}

function applyPreset(presetKey) {
    const preset = UI_PRESETS[presetKey] || UI_PRESETS["mission-control"];
    root.setAttribute("data-ui-preset", presetKey);
    localStorage.setItem(STORAGE_KEYS.preset, presetKey);

    document.querySelectorAll("[data-preset-option]").forEach((element) => {
        element.classList.toggle("is-active", element.dataset.presetOption === presetKey);
    });

    document.querySelectorAll("[data-current-preset-label]").forEach((element) => {
        element.textContent = preset.label;
    });

    document.querySelectorAll("[data-current-preset-copy]").forEach((element) => {
        element.textContent = preset.description;
    });
}

function applyDensity(density) {
    root.setAttribute("data-density", density);
    localStorage.setItem(STORAGE_KEYS.density, density);

    document.querySelectorAll("[data-density-option]").forEach((element) => {
        element.classList.toggle("is-active", element.dataset.densityOption === density);
    });
}

function wireThemeToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const nextTheme = getStoredTheme() === "dark" ? "light" : "dark";
            applyTheme(nextTheme);
        });
    });
}

function wirePresetControls() {
    document.querySelectorAll("[data-preset-option]").forEach((button) => {
        button.addEventListener("click", () => applyPreset(button.dataset.presetOption));
    });

    document.querySelectorAll("[data-density-option]").forEach((button) => {
        button.addEventListener("click", () => applyDensity(button.dataset.densityOption));
    });

    document.querySelectorAll("[data-reset-prefs]").forEach((button) => {
        button.addEventListener("click", () => {
            applyTheme("light");
            applyPreset("mission-control");
            applyDensity("comfortable");
        });
    });
}

function wireUploadForm() {
    const fileInput = document.getElementById("flight-log-input");
    const fileName = document.querySelector("[data-file-name]");
    const dropzone = document.querySelector(".dropzone");
    const submitButton = document.querySelector("[data-submit-label]");

    if (!fileInput || !fileName || !dropzone) {
        return;
    }

    const renderFileName = () => {
        fileName.textContent = fileInput.files?.[0]?.name || "No file selected";
    };

    fileInput.addEventListener("change", renderFileName);

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragover");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragover");
        });
    });

    dropzone.addEventListener("drop", (event) => {
        const files = event.dataTransfer?.files;
        if (!files?.length) {
            return;
        }

        fileInput.files = files;
        renderFileName();
    });

    fileInput.form?.addEventListener("submit", () => {
        if (submitButton) {
            submitButton.textContent = "Processing...";
            submitButton.disabled = true;
        }
    });
}

function wireFileDisplays() {
    document.querySelectorAll("[data-file-display]").forEach((input) => {
        input.addEventListener("change", () => {
            const targetId = input.dataset.fileDisplay;
            const target = targetId ? document.getElementById(targetId) : null;
            if (!target) {
                return;
            }

            target.textContent = input.files?.[0]?.name || "No file selected";
        });
    });
}

function initApp() {
    applyTheme(getStoredTheme());
    applyPreset(getStoredPreset());
    applyDensity(getStoredDensity());
    wireThemeToggle();
    wirePresetControls();
    wireUploadForm();
    wireFileDisplays();
}

document.addEventListener("DOMContentLoaded", initApp);
