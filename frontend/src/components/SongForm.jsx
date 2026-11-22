import React, { useRef, useState } from "react";

const INITIAL_FORM = {
  prompt: "An uplifting synth-pop song about starting over in a new city",
  duration_seconds: 120,
  generation_model: "turbo",
  variation_count: 1,
  genre: "",
  mood: "",
  bpm: null,
  key_scale: "",
  time_signature: "",
  normalize_audio: false,
  fade_in: false,
  fade_out: false,
  vocal_language: "en",
  music_planner: true,
  enhance_prompt: true,
  lm_temperature: 0.85,
  lm_cfg_scale: 2,
  avoid: "",
  inference_steps: 8,
  vocals: true,
  lyrics: "",
  instruments: [],
  vocal_style: "",
  reference_strength: 0.45,
};

function formatDuration(seconds) {
  return seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds} sec`;
}

export function SongForm({ busy, onGenerate }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [referenceFile, setReferenceFile] = useState(null);
  const referenceInput = useRef(null);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number" || ["duration_seconds", "variation_count", "inference_steps"].includes(name)
            ? value === "" ? null : Number(value)
            : value,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (referenceFile && !rightsConfirmed) {
      setError("Confirm that you have permission to use this MP3.");
      return;
    }
    setSubmitting(true);
    try {
      await onGenerate(form, referenceFile);
      setReferenceFile(null);
      if (referenceInput.current) referenceInput.current.value = "";
      setRightsConfirmed(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleInstrument = (instrument) => {
    setForm((current) => ({
      ...current,
      instruments: current.instruments.includes(instrument)
        ? current.instruments.filter((item) => item !== instrument)
        : [...current.instruments, instrument],
    }));
  };

  return (
    <form className="song-form" onSubmit={submit}>
      <label>
        Describe the song
        <textarea
          name="prompt"
          value={form.prompt}
          onChange={update}
          rows="4"
          required
        />
      </label>
      <p className="field-note">
        This description drives the sound and genre. The fields below are
        optional refinements; leave them blank to follow your description.
      </p>
      <div className="grid">
        <label>
          Genre
          <input name="genre" value={form.genre} onChange={update} placeholder="Infer from description" />
        </label>
        <label>
          Mood
          <input name="mood" value={form.mood} onChange={update} placeholder="Infer from description" />
        </label>
        <label>
          BPM
          <input
            name="bpm"
            type="number"
            min="40"
            max="220"
            value={form.bpm ?? ""}
            onChange={update}
            placeholder="Auto"
          />
        </label>
        <label>
          Key
          <select name="key_scale" value={form.key_scale} onChange={update}>
            <option value="">Auto</option>
            {["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"].flatMap((key) => [
              <option key={`${key}-major`} value={`${key} Major`}>{key} Major</option>,
              <option key={`${key}-minor`} value={`${key} minor`}>{key} minor</option>,
            ])}
          </select>
        </label>
        <label>
          Time signature
          <select name="time_signature" value={form.time_signature} onChange={update}>
            <option value="">Auto</option>
            <option value="2">2/4</option>
            <option value="3">3/4</option>
            <option value="4">4/4</option>
            <option value="6">6/8</option>
          </select>
        </label>
      </div>
      <label>
        Song length: {formatDuration(form.duration_seconds)}
        <input
          name="duration_seconds"
          type="range"
          min="30"
          max="120"
          step="30"
          value={form.duration_seconds}
          onChange={update}
        />
      </label>
      <label>
        Generation model
        <select name="generation_model" value={form.generation_model} onChange={update}>
          <option value="turbo">Turbo · Fastest</option>
          <option value="turbo-shift1">Turbo Shift1 · More detail, looser prompt match</option>
          <option value="turbo-shift3">Turbo Shift3 · Fast, clearer timbre</option>
          <option value="sft">SFT · Balanced detail and prompt guidance</option>
          <option value="xl-turbo">XL Turbo · Fast, higher detail</option>
          <option value="xl-sft">XL SFT · Highest detail, slowest</option>
        </select>
      </label>
      {form.generation_model !== "turbo" && (
        <p className="field-note">
          Switching models can take extra time on the first use while ACE-Step
          downloads or loads the checkpoint. SFT models use 50 steps; Turbo
          models use 8. Larger XL models need more GPU memory. Shift1 can add
          detail but may follow the prompt less closely.
        </p>
      )}
      <label>
        Variations
        <select name="variation_count" value={form.variation_count} onChange={update}>
          <option value="1">1 song</option>
          <option value="3">3 songs to compare</option>
        </select>
      </label>
      {form.variation_count > 1 && (
        <p className="field-note">
          Variations generate one after another and take about three times as
          long. You can compare and download each result.
        </p>
      )}
      <fieldset className="instruments">
        <legend>Sound finishing</legend>
        <label className="instrument">
          <input type="checkbox" name="normalize_audio" checked={form.normalize_audio} onChange={update} />
          <span>Loudness normalize for consistent volume</span>
        </label>
        <label className="instrument">
          <input type="checkbox" name="fade_in" checked={form.fade_in} onChange={update} />
          <span>2 second fade in</span>
        </label>
        <label className="instrument">
          <input type="checkbox" name="fade_out" checked={form.fade_out} onChange={update} />
          <span>3 second fade out</span>
        </label>
      </fieldset>
      <details className="advanced-options">
        <summary>Advanced sound controls</summary>
        <label className="instrument">
          <input type="checkbox" name="music_planner" checked={form.music_planner} onChange={update} />
          <span>Use ACE-Step composition planner</span>
        </label>
        <p className="field-note">
          Helps plan melody and arrangement, but adds generation time. Turn it
          off for faster direct generation.
        </p>
        <label className="instrument">
          <input type="checkbox" name="enhance_prompt" checked={form.enhance_prompt} onChange={update} />
          <span>Let ACE-Step expand my description</span>
        </label>
        <p className="field-note">
          The music planner can add production and arrangement details. Turn it
          off to keep the caption closer to your original wording.
        </p>
        <div className="grid">
          <label>
            Creativity: {Number(form.lm_temperature).toFixed(2)}
            <input name="lm_temperature" type="range" min="0" max="1.5" step="0.05" value={form.lm_temperature} onChange={update} />
          </label>
          <label>
            Prompt adherence: {Number(form.lm_cfg_scale).toFixed(1)}
            <input name="lm_cfg_scale" type="range" min="1" max="4" step="0.1" value={form.lm_cfg_scale} onChange={update} />
          </label>
        </div>
        <p className="field-note">
          More creativity can make results less predictable. Stronger prompt
          adherence can reduce variation. These controls apply to the ACE-Step
          music planner.
        </p>
        <label>
          Avoid sounds or styles
          <input name="avoid" value={form.avoid} onChange={update} maxLength="300" placeholder="e.g. muddy mix, crowd noise, distorted vocals" />
        </label>
        <p className="field-note">
          This guides the planner away from those traits; it cannot guarantee
          they will be absent.
        </p>
        {["turbo", "turbo-shift1", "turbo-shift3", "xl-turbo"].includes(form.generation_model) && (
          <label>
            Turbo detail steps
            <select name="inference_steps" value={form.inference_steps} onChange={update}>
              <option value="8">8 · Recommended, faster</option>
              <option value="12">12 · More refinement, slower</option>
              <option value="16">16 · Most refinement, slowest</option>
            </select>
          </label>
        )}
        {["turbo", "turbo-shift1", "turbo-shift3", "xl-turbo"].includes(form.generation_model) && (
          <p className="field-note">
            More Turbo steps give the model more time to refine the audio but
            increase generation time. The default 8-step setting is ACE-Step's
            recommended Turbo setting.
          </p>
        )}
        {form.vocals && (
          <label>
            Vocal language
            <select name="vocal_language" value={form.vocal_language} onChange={update}>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="pt">Portuguese</option>
              <option value="unknown">Auto detect</option>
            </select>
          </label>
        )}
      </details>
      <label>
        Lyrics (leave blank to write them)
        <textarea
          name="lyrics"
          value={form.lyrics}
          onChange={update}
          rows="5"
          placeholder="[Verse 1 - intimate]&#10;Your lyrics&#10;&#10;[Chorus - powerful]&#10;Sing-along line"
        />
      </label>
      <p className="field-note">
        Vocal requests emphasize natural phrasing, clear words, and your lyrics
        verbatim. Performance quality varies by generation.
      </p>
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
      <div className="grid vocal-controls">
        <label>
          Vocal style
          <input
            name="vocal_style"
            value={form.vocal_style}
            onChange={update}
            disabled={!form.vocals}
            placeholder="e.g. warm, raspy soul singer"
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
      <p className="field-note">
        Describe the singer’s tone and delivery here, such as “warm, raspy soul
        singer with powerful belting.” Results vary by prompt and lyrics.
      </p>
      <label>
        MP3 reference for style and structure (optional)
        <input
          ref={referenceInput}
          type="file"
          accept=".mp3,audio/mpeg"
          onChange={(event) => setReferenceFile(event.target.files?.[0] || null)}
        />
      </label>
      {referenceFile && (
        <>
          <label>
            Reference influence: {Math.round(form.reference_strength * 100)}%
            <input
              name="reference_strength"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={form.reference_strength}
              onChange={update}
            />
          </label>
          <p className="field-note">
            Lower values let the song description change the style more. Higher
            values follow the reference more closely. The original recording is
            used as a guide and is not added to the final mix.
          </p>
          <label className="toggle rights-check">
            <input
              type="checkbox"
              checked={rightsConfirmed}
              onChange={(event) => setRightsConfirmed(event.target.checked)}
            />
            <span>I have permission to use this recording.</span>
          </label>
        </>
      )}
      {error && <p className="inline-error">{error}</p>}
      <button type="submit" disabled={busy || submitting}>
        {busy || submitting ? "Starting..." : "Generate song"}
      </button>
    </form>
  );
}
