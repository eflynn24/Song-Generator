import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api";

function App() {
  const [form, setForm] = useState({
    prompt: "An uplifting synth-pop song about starting over in a new city",
    genre: "Synth-pop",
    mood: "Hopeful",
    bpm: 110,
    duration_seconds: 30,
    vocals: true,
    lyrics: "[Verse 1]\nWalking out beneath the morning sky\n[Chorus]\nWe're alive, we're chasing every light",
    instruments: ["guitar", "piano", "bass", "drums", "saxophone"],
    vocal_style: "Warm pop vocalist",
  });
  const [health, setHealth] = useState(null);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((response) => response.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "error", ollama: false }));
  }, []);

  useEffect(() => {
    if (!job || !["queued", "generating"].includes(job.status)) {
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API}/jobs/${job.id}`);
        setJob(await response.json());
      } catch {
        // The next poll will retry while the backend is unavailable.
      }
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [job, busy]);

  const update = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number"
            ? Number(value)
            : value,
    }));
  };

  const toggleInstrument = (instrument) => {
    setForm((current) => ({
      ...current,
      instruments: current.instruments.includes(instrument)
        ? current.instruments.filter((item) => item !== instrument)
        : [...current.instruments, instrument],
    }));
  };

  const generate = async (event) => {
    event.preventDefault();
    setBusy(true);
    setJob(null);
    try {
      const response = await fetch(`${API}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        throw new Error("Could not start generation");
      }
      setJob(await response.json());
    } catch (error) {
      setJob({ status: "failed", error: error.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">Studio / Local</p>
          <h1>Song Generator</h1>
        </div>
        <div className="status" title="Local backend status">
          <span className={health?.status === "ok" ? "online" : ""} />
          {health?.status === "ok" ? "Backend online" : "Connecting"}
        </div>
      </header>

      <section className="workspace">
        <form onSubmit={generate}>
          <label>
            Describe the song
            <textarea
              name="prompt"
              value={form.prompt}
              onChange={update}
              rows="5"
              required
            />
          </label>

          <div className="grid">
            <label>
              Instrument style
              <input name="genre" value={form.genre} onChange={update} />
            </label>
            <label>
              Mood
              <input name="mood" value={form.mood} onChange={update} />
            </label>
            <label>
              BPM
              <input
                name="bpm"
                type="number"
                min="40"
                max="220"
                value={form.bpm}
                onChange={update}
              />
            </label>
            <label>
              Length
              <select
                name="duration_seconds"
                value={form.duration_seconds}
                onChange={update}
              >
                <option value="30">30 seconds</option>
                <option value="60">60 seconds</option>
                <option value="120">2 minutes</option>
                <option value="180">3 minutes</option>
              </select>
            </label>
          </div>

          <label>
            Apply lyrics
            <textarea
              name="lyrics"
              value={form.lyrics}
              onChange={update}
              rows="6"
              placeholder="[Verse 1]&#10;Your lyrics&#10;[Chorus]&#10;Sing-along line"
            />
          </label>

          <fieldset className="instruments">
            <legend>Instruments</legend>
            {["guitar", "piano", "bass", "drums", "saxophone", "strings"].map(
              (instrument) => (
                <label key={instrument} className="instrument">
                  <input
                    type="checkbox"
                    checked={form.instruments.includes(instrument)}
                    onChange={() => toggleInstrument(instrument)}
                  />
                  <span>{instrument}</span>
                </label>
              ),
            )}
          </fieldset>

          <div className="grid">
            <label>
              Vocal style
              <input
                name="vocal_style"
                value={form.vocal_style}
                onChange={update}
                disabled={!form.vocals}
              />
            </label>
            <label className="toggle vocals-toggle">
              <input
                name="vocals"
                type="checkbox"
                checked={form.vocals}
                onChange={update}
              />
              <span>Singing vocals</span>
            </label>
          </div>

          <div className="arrangement-note">
            <span>Arrangement</span>
            <strong>Drums · Bass · Synth pad · Melody</strong>
          </div>

          <button type="submit" disabled={busy}>
            {busy ? "Generating..." : "Generate song"}
          </button>
        </form>

        <aside>
          {job ? (
            <>
              {job.status === "completed" ? (
                <div className="result">
                  <p className="eyebrow">Generated result</p>
                  <h2>{job.title}</h2>
                  <audio
                    key={job.id}
                    controls
                    preload="metadata"
                    src={job.mp3_url || job.audio_url}
                  >
                    Your browser does not support audio playback.
                  </audio>
                  <a
                    className="download"
                    href={job.mp3_url || job.audio_url}
                    download
                  >
                    Download MP3
                  </a>
                  <pre>{job.lyrics}</pre>
                </div>
              ) : job.status === "failed" ? (
                <div className="empty error">
                  <h2>Generation failed</h2>
                  <p>{job.error}</p>
                </div>
              ) : (
                <div className="empty loading">
                  <div className="spinner" />
                  <h2>Writing and arranging</h2>
                  <p>Connecting to local models...</p>
                </div>
              )}
            </>
          ) : (
            <div className="empty">
              <div className="wave" aria-hidden="true">
                {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                  <span key={n} />
                ))}
              </div>
              <h2>Your song will appear here</h2>
              <p>Enter an idea, choose a direction, and start generating.</p>
              <div className="model-state">
                Ollama: {health?.ollama ? "connected" : "fallback mode"}
              </div>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

