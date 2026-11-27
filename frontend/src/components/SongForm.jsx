import React, { useRef, useState } from "react";

const INITIAL_FORM = {
  prompt: "",
  duration_seconds: 120,
  generation_model: "turbo",
  variation_count: 1,
  variation_prompts: [],
  genres: [],
  key_scale: "",
  vocal_language: "en",
  lyrics: "",
  instruments: [],
  vocal_preset: "natural",
  music_planner: true,
  studio_master: true,
  reference_strength: 0.7,
};

function formatDuration(seconds) {
  return seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds} sec`;
}

const GENRES = [
  { value: "Pop", label: "Pop", description: "A catchy, uplifting pop song with a bright lead melody, tight drums, warm bass, and a clear verse-to-chorus lift.", enhancements: ["Open with a short, instantly memorable hook, then let the chorus bloom with bright layered harmonies and polished drums.", "Keep the verses close and rhythmic; make the chorus wider, more melodic, and easy to sing along with.", "Use a crisp pop beat, a focused bass line, and small synth or guitar accents that build toward a big final chorus."] },
  { value: "Rock", label: "Rock", description: "A driving rock song with live drums, electric-guitar riffs, steady bass, and an energetic band performance.", enhancements: ["Start with a bold guitar riff, bring the full band in with punchy live drums, and lift the chorus with wider guitars.", "Give the verses a tight, restrained groove, then release into a louder sing-along chorus with a strong backbeat.", "Let the bass and drums push the song forward while gritty guitar layers add energy and a memorable instrumental break."] },
  { value: "Hip-hop / rap", label: "Hip-hop / rap", description: "A confident hip-hop track with a deep, controlled bass line, crisp drums, and rhythmic vocal phrasing.", enhancements: ["Build the beat around a distinctive drum pattern and a deep bass pulse, leaving space for the vocal rhythm to lead.", "Use a sparse, head-nodding verse groove, then add a memorable melodic refrain and extra percussion for the hook.", "Layer subtle samples or synth textures around punchy kicks and snares; keep the low end clear and the vocal forward."] },
  { value: "R&B / soul", label: "R&B / soul", description: "A soulful R&B song with expressive vocals, warm bass, rich chords, and a relaxed, pocket-focused groove.", enhancements: ["Settle into a laid-back groove with warm electric piano, rounded bass, and expressive vocal runs at the ends of lines.", "Let the verse feel intimate and syncopated, then open the chorus with stacked harmonies and richer chords.", "Use subtle percussion and lush chord colors while keeping the lead vocal close, emotional, and clearly in front."] },
  { value: "Country", label: "Country", description: "A story-led country song with a steady band groove, twangy guitars, warm bass, and an organic vocal performance.", enhancements: ["Anchor the arrangement with acoustic strumming and a steady kick-snare groove, adding pedal steel or fiddle between vocal lines.", "Keep the verses conversational and story-focused, then raise the energy with a broad, heartfelt chorus.", "Use bright picked guitar, grounded bass, and natural harmonies to give the song a lived-in, full-band feel."] },
  { value: "Jazz", label: "Jazz", description: "A jazz song with expressive phrasing, rich harmony, nimble bass and drums, and room for instrumental interplay.", enhancements: ["Give the rhythm section a relaxed swing, let piano or guitar color the chords, and answer vocal phrases with a melodic solo.", "Use tasteful extensions and a nimble bass line; vary the groove between the intimate verse and more open chorus.", "Let the ensemble trade short melodic phrases over a warm, lightly syncopated groove, building to a graceful ending."] },
  { value: "Electronic / EDM", label: "Electronic / EDM", description: "An electronic dance track with a precise beat, layered synth textures, a strong bass pulse, and a rising build.", enhancements: ["Introduce a pulsing synth motif over a clean beat, build tension with filtered layers, then release into a full, melodic drop.", "Keep the low end tight and danceable, use bright arpeggiated textures, and create clear contrast between breakdown and drop.", "Shape the track with evolving electronic layers and a steady kick, saving the widest synths and strongest drums for the climax."] },
  { value: "Indie / alternative", label: "Indie / alternative", description: "An indie alternative song with distinctive guitar or synth textures, dynamic band interplay, and an expressive, unforced vocal.", enhancements: ["Choose one unusual guitar or synth texture as a musical signature, then let the band grow gradually around it.", "Keep the first verse close and understated; make the chorus wider with layered guitars and a more urgent drum part.", "Use natural-sounding drums, slightly rough-edged textures, and a melodic hook that feels personal rather than overly polished."] },
  { value: "Folk / acoustic", label: "Folk / acoustic", description: "An intimate acoustic song with natural dynamics, clear storytelling, and a warm string-led arrangement.", enhancements: ["Lead with fingerpicked acoustic guitar and close vocals, adding gentle harmony and light percussion only as the song grows.", "Let the lyric and melody stay central; use acoustic strumming, subtle strings, and a soft lift into the chorus.", "Create a live, human feel with changing guitar patterns, warm room ambience, and a restrained instrumental turn."] },
  { value: "Metal", label: "Metal", description: "A heavy metal song with distorted guitar riffs, forceful drums, powerful bass, and dramatic dynamic shifts.", enhancements: ["Drive the verses with palm-muted guitar and tight kick drums, then open into a wide, forceful chorus riff.", "Use a memorable heavy riff as the main motif, with punchy drums and a contrasting half-time bridge before the final chorus.", "Keep the guitars dense but defined; use sharp rhythmic stops, strong bass support, and a dramatic instrumental section."] },
  { value: "Reggae", label: "Reggae", description: "A relaxed reggae song with offbeat guitar or keyboard chops, a rounded bass line, and an easy, steady groove.", enhancements: ["Let the bass carry a relaxed one-drop groove while guitar and keyboard add crisp offbeat accents.", "Keep the rhythm spacious and unhurried, with light percussion, warm chords, and a melodic chorus that floats over the groove.", "Use a buoyant bass pattern and short skanking chords; add small horn or organ responses between vocal lines."] },
  { value: "Blues", label: "Blues", description: "A blues song with soulful phrasing, expressive guitar, a grounded rhythm section, and a strong shuffle feel.", enhancements: ["Set a steady shuffle, answer the vocal with expressive guitar fills, and build the final chorus with a short solo.", "Use a warm, gritty guitar tone and conversational vocal phrasing over a simple, confident blues groove.", "Let the rhythm section stay deep and steady while guitar and piano trade call-and-response phrases."] },
  { value: "Classical / cinematic", label: "Classical / cinematic", description: "A cinematic orchestral song with evolving motifs, broad dynamics, and a clear emotional rise and resolution.", enhancements: ["Begin with a small piano or string motif, gradually add orchestral layers, and reach a sweeping but controlled climax.", "Use low strings for tension, delicate high textures for space, and a memorable theme that returns in a fuller arrangement.", "Shape the song like a film cue: quiet opening, gradual harmonic lift, dramatic peak, and a resolved final cadence."] },
  { value: "Latin", label: "Latin", description: "A lively Latin song with syncopated percussion, a danceable pulse, warm bass, and bright rhythmic accents.", enhancements: ["Build the groove from hand percussion and syncopated bass, adding bright guitar or piano patterns around the vocal.", "Keep the rhythm buoyant and danceable, with percussion fills leading into a catchy chorus and lively instrumental break.", "Use interlocking percussion, warm chords, and short call-and-response phrases to keep the arrangement moving."] },
  { value: "Funk / disco", label: "Funk / disco", description: "A dance-ready funk disco song with tight drums, syncopated bass, bright rhythmic accents, and an infectious hook.", enhancements: ["Put a tight, syncopated bass riff at the center, lock it to crisp drums, and add bright guitar or keyboard chops.", "Keep the groove steady and physical, using brass or synth stabs to punctuate the hook and lift the chorus.", "Build a polished dance-floor pulse with rhythmic guitar, lively bass fills, and a celebratory final refrain."] },
];

const GENRE_BLEND_PHRASES = {
  Pop: "bright melodic hooks, polished production, and a big singable chorus",
  Rock: "driving electric-guitar riffs, live drums, and energetic band dynamics",
  "Hip-hop / rap": "a beat-led groove, deep bass, crisp drums, and rhythmic vocal phrasing",
  "R&B / soul": "rich chords, expressive vocals, warm bass, and a relaxed pocket",
  Country: "storytelling vocals, twangy guitars, and a warm organic rhythm section",
  Jazz: "expressive phrasing, rich harmony, and nimble instrumental interplay",
  "Electronic / EDM": "precise dance beats, layered synths, and rising builds",
  "Indie / alternative": "distinctive textures, dynamic band interplay, and an unforced feel",
  "Folk / acoustic": "acoustic strings, intimate vocals, and natural dynamics",
  Metal: "heavy guitar riffs, forceful drums, and dramatic dynamic shifts",
  Reggae: "offbeat guitar or keyboard chops and an easy, bass-led groove",
  Blues: "soulful phrasing, expressive guitar, and a steady shuffle",
  "Classical / cinematic": "orchestral colors, evolving motifs, and a dramatic emotional arc",
  Latin: "syncopated percussion, warm bass, and a lively dance pulse",
  "Funk / disco": "syncopated bass, tight drums, and bright dance-floor accents",
};

const ENHANCEMENT_CYCLES = [
  "Shape the arrangement with a memorable opening, a clear verse-to-chorus lift, and a satisfying final section.",
  "Create contrast between sections: make the verses more restrained, the chorus more open, and the bridge feel fresh.",
  "Give the melody a distinct motif that returns in the chorus, and make the ending feel intentional rather than abrupt.",
  "Keep the mix focused: clear lead vocal, defined low end, and space for the featured instruments to stand out.",
];

function describeGenres(genres) {
  if (genres.length === 1) return genres[0].description;
  if (!genres.length) return "";
  if (genres.length === 2 && genres.some((genre) => genre.value === "Rock") && genres.some((genre) => genre.value === "Blues")) {
    return "A blues-rock song combining rock energy with blues phrasing: overdriven electric-guitar riffs, expressive bent guitar notes, electric bass, live drums, and a strong backbeat.";
  }
  const orderedGenres = [...genres].sort((left, right) => left.label.localeCompare(right.label));
  const labels = orderedGenres.map((genre) => genre.label).join(" + ");
  const styleDetails = orderedGenres.map((genre) => GENRE_BLEND_PHRASES[genre.value]).join("; ");
  return `A ${labels} fusion song that blends ${styleDetails}. Keep each genre recognizable while making the rhythm section, melody, and production feel like one cohesive song.`;
}

function joinPrompt(base, direction) {
  const idea = base.trim().replace(/[.!?]+$/, "");
  const detail = direction.trim();
  return [idea, detail].filter(Boolean).join(". ").slice(0, 2000);
}

export function SongForm({ busy, minimaxAvailable, onGenerate }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const instrumental = form.vocal_preset === "instrumental";
  const usesMiniMax = form.generation_model === "minimax-music3";
  const [referenceFile, setReferenceFile] = useState(null);
  const referenceInput = useRef(null);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [promptNotice, setPromptNotice] = useState("");
  const enhancementCycle = useRef(0);
  const promptSource = useRef(INITIAL_FORM.prompt);
  const generatedPrompt = useRef("");

  const update = (event) => {
    const { name, value, type, checked } = event.target;
    if (name === "prompt") {
      promptSource.current = value;
      generatedPrompt.current = "";
    }
    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
            : ["duration_seconds", "variation_count"].includes(name)
            ? value === "" ? null : Number(value)
            : value,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!usesMiniMax && referenceFile && !rightsConfirmed) {
      setError("Confirm that you have permission to use this MP3.");
      return;
    }
    setSubmitting(true);
    try {
      await onGenerate({
        ...form,
        vocals: !instrumental,
        vocal_preset: instrumental ? "auto" : form.vocal_preset,
        lyrics: instrumental ? "" : form.lyrics,
      }, usesMiniMax ? null : referenceFile);
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

  const toggleGenre = (genre) => {
    const selectedGenres = form.genres.includes(genre)
      ? form.genres.filter((item) => item !== genre)
      : [...form.genres, genre];
    const selected = selectedGenres
      .map((value) => GENRES.find((item) => item.value === value))
      .filter(Boolean);
    const source = generatedPrompt.current === form.prompt
      ? promptSource.current
      : form.prompt;
    const genreDescription = describeGenres(selected);
    const prompt = selected.length
      ? joinPrompt(source, genreDescription)
      : source;
    const boundedPrompt = prompt.slice(0, 2000);
    promptSource.current = source;
    generatedPrompt.current = selected.length && boundedPrompt !== source ? boundedPrompt : "";
    setForm((current) => ({
      ...current,
      genres: selectedGenres,
      prompt: boundedPrompt,
    }));
    setPromptNotice(selected.length
      ? `Song description updated for ${selected.map((item) => item.label).join(" + ")}.`
      : "Genre direction removed from the description.");
  };

  const enhancePrompt = () => {
    const basePrompt = generatedPrompt.current === form.prompt
      ? promptSource.current
      : form.prompt;
    const selected = form.genres
      .map((value) => GENRES.find((item) => item.value === value))
      .filter(Boolean)
      .sort((left, right) => left.label.localeCompare(right.label));
    const cycle = enhancementCycle.current++;
    const genreDirection = selected.length
      ? `Make this a clearly recognizable ${selected.map((item) => item.label).join(" + ")} song. ${selected.map((item) => item.enhancements[cycle % item.enhancements.length]).join(" Blend these genre elements naturally. ")}`
      : "Choose a coherent genre and make its rhythm, instrumentation, and production easy to recognize.";
    const instruments = form.instruments.length
      ? `Feature ${form.instruments.join(", ")} clearly in the arrangement.`
      : "Choose instruments that fit the style and keep each part distinct.";
    const enhancedPrompt = joinPrompt(basePrompt, [
      genreDirection,
      instruments,
      ENHANCEMENT_CYCLES[cycle % ENHANCEMENT_CYCLES.length],
      "Keep the mix balanced, with vocals easy to understand when present.",
    ].join(" ")).slice(0, 2000);
    promptSource.current = basePrompt;
    generatedPrompt.current = enhancedPrompt;
    setForm((current) => ({
      ...current,
      prompt: enhancedPrompt,
    }));
    setPromptNotice("Prompt refined for the selected genre. Click again for a different arrangement direction.");
  };

  return (
    <form className="song-form" onSubmit={submit}>
      <label>
        Describe the song
        <textarea
          name="prompt"
          value={form.prompt}
          onChange={update}
          placeholder="Describe your song, or select a genre to build a starting description."
          maxLength={2000}
          rows="4"
          required
        />
        <span className="field-note">
          Open in your browser: <a href={window.location.origin} target="_blank" rel="noreferrer">{window.location.host}</a>
        </span>
      </label>
      <button className="secondary-button prompt-enhance-button" type="button" onClick={enhancePrompt}>
        Enhance prompt
      </button>
      {promptNotice && <p className="field-note" aria-live="polite">{promptNotice}</p>}
      <p className="field-note">
        Choosing genres builds a matching description here. Enhance prompt
        replaces it with a fresh, genre-specific direction each time.
      </p>
      <fieldset className="instruments genre-options">
        <legend>Genres</legend>
        {GENRES.map(({ value, label }) => (
          <label key={value} className="instrument">
            <input
              type="checkbox"
              checked={form.genres.includes(value)}
              onChange={() => toggleGenre(value)}
            />
            <span>{label}</span>
          </label>
        ))}
      </fieldset>
      <p className="field-note">Select one genre or combine a few. Your choices are sent directly to the music model.</p>
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
          <option value="turbo-lite">Turbo Lite · Fastest, planner off</option>
          <option value="turbo">Turbo · Fast with 0.6B planner</option>
          <option value="turbo-shift1">Turbo Shift1 · More detail, looser prompt match</option>
          <option value="turbo-shift3">Turbo Shift3 · Fast, clearer timbre</option>
          <option value="sft">SFT · Higher detail and prompt guidance</option>
          <option value="xl-turbo">XL Turbo · 4B, fast with more detail</option>
          <option value="xl-sft">XL SFT · 4B, detailed studio takes</option>
          {minimaxAvailable && <option value="minimax-music3">MiniMax Music 3 · 11B, detailed songs</option>}
        </select>
      </label>
      <label>
        Versions to generate
        <select name="variation_count" value={form.variation_count} onChange={update}>
          <option value="1">1 version</option>
          <option value="2">2 versions</option>
          <option value="3">3 versions</option>
        </select>
      </label>
      {form.variation_count > 1 && Array.from({ length: form.variation_count }, (_, index) => (
        <label key={index}>
          Version {index + 1} direction (optional)
          <input
            value={form.variation_prompts[index] || ""}
            maxLength={500}
            placeholder={index === 0 ? "e.g. sparse acoustic opening" : "e.g. bigger chorus and brighter drums"}
            onChange={(event) => setForm((current) => {
              const variation_prompts = [...current.variation_prompts];
              variation_prompts[index] = event.target.value;
              return { ...current, variation_prompts };
            })}
          />
        </label>
      ))}
      {form.variation_count > 1 && <p className="field-note">Each version uses a different saved seed. Leave directions blank for alternate takes of the same description.</p>}
      {form.generation_model === "turbo-lite" && (
        <p className="field-note">
          Uses the same 2B Turbo audio model, but skips the 0.6B composition
          planner pass for quicker generation. Song structure may be less planned.
        </p>
      )}
      {!usesMiniMax && form.generation_model !== "turbo-lite" && !referenceFile && (
        <label className="toggle">
          <input name="music_planner" type="checkbox" checked={form.music_planner} onChange={update} />
          <span>Composition planner · More arrangement guidance, longer generation</span>
        </label>
      )}
      {!usesMiniMax && !["turbo", "turbo-lite"].includes(form.generation_model) && (
        <p className="field-note">
          Switching models can take extra time on the first use while ACE-Step
          downloads or loads the checkpoint. SFT models use 50 steps; Turbo
          models use 8. Larger XL models need more GPU memory. Shift1 can add
          detail but may follow the prompt less closely.
        </p>
      )}
      {usesMiniMax && (
        <p className="field-note">Uses your description and lyrics. Song length is a maximum, and generation can take several minutes.</p>
      )}
      <label>
        Vocal preset
        <select name="vocal_preset" value={form.vocal_preset} onChange={update}>
          <option value="auto">From song description</option>
          <option value="natural">Natural lead · Close mic, audible breaths</option>
          <option value="clear">Clear pop lead</option>
          <option value="intimate">Intimate acoustic</option>
          <option value="soul">Warm soul</option>
          <option value="rock">Gritty rock</option>
          <option value="harmonies">Chorus harmonies</option>
          <option value="instrumental">Instrumental</option>
        </select>
      </label>
      {!instrumental && (
        <>
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
        </>
      )}
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
      <label className="toggle">
        <input name="studio_master" type="checkbox" checked={form.studio_master} onChange={update} />
        <span>Studio master · Even loudness, 24-bit WAV and 320 kbps MP3</span>
      </label>
      {!usesMiniMax && (
        <label>
          MP3 reference for style and structure (optional)
          <input
            ref={referenceInput}
            type="file"
            accept=".mp3,audio/mpeg"
            onChange={(event) => setReferenceFile(event.target.files?.[0] || null)}
          />
        </label>
      )}
      {!usesMiniMax && referenceFile && (
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
            The default 70% keeps more of the reference feel. Lower values
            (around 30–50%) give your description more freedom; higher values
            follow the reference more closely. The recording guides generation
            and is not added to the final mix.
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
      <button type="submit" disabled={submitting}>
        {submitting ? "Adding to queue..." : "Add song to queue"}
      </button>
    </form>
  );
}
