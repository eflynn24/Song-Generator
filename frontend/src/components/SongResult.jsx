import React, { useEffect, useState } from "react";

export function SongResult({ job }) {
  const [progress, setProgress] = useState(0);
  const [variation, setVariation] = useState(1);

  useEffect(() => setVariation(1), [job?.id]);

  useEffect(() => {
    if (job?.status !== "generating") {
      setProgress(0);
      return undefined;
    }

    setProgress(10);
    const timer = window.setInterval(() => {
      setProgress((current) => Math.min(current + 1, 95));
    }, 4000);
    return () => window.clearInterval(timer);
  }, [job?.status, job?.id]);

  if (!job) {
    return (
      <div className="empty">
        <div className="wave" aria-hidden="true">
          {[1, 2, 3, 4, 5, 6, 7].map((n) => <span key={n} />)}
        </div>
        <h2>Your song will appear here</h2>
        <p>Describe a song, choose a direction, and generate.</p>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="empty error">
        <h2>Generation failed</h2>
        <p>{job.error}</p>
      </div>
    );
  }

  if (job.status !== "completed") {
    const queued = job.status === "queued";
    const displayedProgress = queued ? 0 : progress;
    const duration = job.request?.duration_seconds ?? 30;
    const durationLabel = duration % 60 === 0
      ? `${duration / 60}-minute song`
      : `${duration}-second song`;
    return (
      <div className="empty loading" role="status" aria-live="polite">
        <div className="spinner" />
        <h2>{queued ? "Queued for generation" : "Making your song"}</h2>
        <div className="generation-progress-label">
          <span>Estimated progress</span>
          <span>{displayedProgress}%</span>
        </div>
        <div
          className="generation-progress"
          role="progressbar"
          aria-label="Song generation progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={displayedProgress}
          aria-valuetext={`${displayedProgress}% estimated`}
        >
          <span style={{ width: `${displayedProgress}%` }} />
        </div>
        <p>
          {queued
            ? "Waiting for the generator to become available."
            : displayedProgress >= 95
              ? `The model is still processing your ${durationLabel}; the percentage is only an estimate.`
              : `Generating your ${durationLabel}. This may take a few minutes.`}
        </p>
      </div>
    );
  }

  return (
    <div className="result">
      <p className="eyebrow">Generated result</p>
      <h2>{job.title}</h2>
      {job.request?.variation_count > 1 && (
        <label>
          Compare variation
          <select value={variation} onChange={(event) => setVariation(Number(event.target.value))}>
            {Array.from({ length: job.request.variation_count }, (_, index) => index + 1).map((number) => (
              <option key={number} value={number}>Variation {number}</option>
            ))}
          </select>
        </label>
      )}
      {job.request?.variation_count > 1 && (
        <p className="field-note">
          Seed {job.request.variation_seeds?.[variation - 1] ?? "unknown"}
          {job.request.variation_prompts?.[variation - 1] && ` · ${job.request.variation_prompts[variation - 1]}`}
        </p>
      )}
      <audio controls preload="metadata" src={`${job.mp3_url || job.audio_url}${variation > 1 ? `?variation=${variation}` : ""}`}>
        Your browser does not support audio playback.
      </audio>
      <a className="download" href={`${job.mp3_url || job.audio_url}${variation > 1 ? `?variation=${variation}` : ""}`} download>
        Download MP3{job.request?.variation_count > 1 ? ` · Variation ${variation}` : ""}
      </a>
      {job.wav_url && variation === 1 && (
        <a className="download" href={job.wav_url} download>
          Download{job.request?.studio_master ? " 24-bit" : ""} WAV
        </a>
      )}
      <pre>{job.lyrics}</pre>
    </div>
  );
}
