import { useEffect, useState } from "react";

const presets = [
  {
    id: "mission-control",
    name: "Mission Control",
    copy: "Balanced default for metrics, summaries, and charts."
  },
  {
    id: "field-ops",
    name: "Field Ops",
    copy: "Higher contrast look for live demos and quick scanning."
  },
  {
    id: "blueprint",
    name: "Blueprint",
    copy: "Minimal neutral shell for building your own component system."
  }
];

export default function App() {
  const [status, setStatus] = useState("Checking backend...");
  const [selectedPreset, setSelectedPreset] = useState(presets[0].id);

  useEffect(() => {
    async function pingBackend() {
      try {
        const response = await fetch("/health");
        if (!response.ok) throw new Error("Backend unavailable");
        setStatus("Backend connected");
      } catch (error) {
        setStatus("Backend not reachable");
      }
    }

    pingBackend();
  }, []);

  const activePreset = presets.find((preset) => preset.id === selectedPreset) ?? presets[0];

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">React workspace</p>
          <h1>Frontend is ready to grow beside your FastAPI backend.</h1>
          <p className="hero-copy">
            This React app is separate from the current server-rendered pages, so you can iterate on
            components, client-side state, and API integrations without breaking the existing flow.
          </p>
        </div>
        <div className="status-card">
          <span className={`status-dot ${status === "Backend connected" ? "is-live" : ""}`} />
          <strong>{status}</strong>
          <p>Vite proxies requests to the backend on <code>127.0.0.1:8000</code>.</p>
        </div>
      </header>

      <main className="workspace-grid">
        <section className="panel">
          <p className="eyebrow">Starter layout</p>
          <h2>Preset playground</h2>
          <div className="preset-grid">
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`preset-card ${selectedPreset === preset.id ? "is-active" : ""}`}
                onClick={() => setSelectedPreset(preset.id)}
              >
                <strong>{preset.name}</strong>
                <span>{preset.copy}</span>
              </button>
            ))}
          </div>
        </section>

        <aside className="panel">
          <p className="eyebrow">Selected preset</p>
          <h2>{activePreset.name}</h2>
          <p>{activePreset.copy}</p>
          <div className="feature-list">
            <span>React 18</span>
            <span>Vite dev server</span>
            <span>FastAPI proxy</span>
            <span>Component-ready</span>
          </div>
        </aside>
      </main>
    </div>
  );
}
