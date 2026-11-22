# Local Song Generator

A self-hosted song studio with temporary guest sessions, persistent user
libraries, AI-written lyrics, and ACE-Step audio generation.

## Install and run

Requirements: Docker Compose, an NVIDIA GPU with the NVIDIA Container Toolkit,
and enough disk space for model weights. ACE-Step Turbo is selected by default.
The 0.6B music planner runs through PyTorch on the CPU, and both the DiT and
other components are offloaded to CPU to reduce GPU memory use. This low-memory
configuration can be slower. Set `ACESTEP_OFFLOAD_DIT_TO_CPU=false` in `.env`
to trade GPU memory use for speed when the GPU has enough room. The ACE-Step
model choices remain available; XL models still require more system and GPU
memory.

```bash
./install.sh
./run.sh
```

The installer creates `.env` if needed, builds the containers, downloads the
default Ollama lyrics model (`llama3.2`), and initializes ACE-Step. It generates
a private one-time password for the default `user` account and prints it once;
change it at first login. Models remain in Docker volumes. Installation can
take a long time.

Open [http://localhost:5173](http://localhost:5173). Sign in, create an account,
or choose **Continue as guest**. The API documentation is at
[http://localhost:8000/docs](http://localhost:8000/docs).

## Using the studio

- Describe the song in plain language. Genre, mood, tempo, instruments, and
  vocal style are optional overrides; leave them blank to let the description
  guide generation.
- Choose a song length from 30 seconds to 2 minutes.
- Choose among ACE-Step models: **Turbo** for fastest generation,
  **Turbo Shift1** for more detail with looser prompt matching,
  **Turbo Shift3** for clearer timbre, **SFT** for more detail and prompt
  guidance, **XL Turbo** for a larger model at Turbo speed, or **XL SFT** for
  the most detailed slower option. Additional checkpoints download the first
  time they are selected and XL models need more GPU memory.
- Generate one song or three sequential variations to compare. Three options
  take about three times as long. You can select and download each MP3.
- Optionally specify musical key and time signature, apply loudness
  normalization for more consistent playback volume, and add a short fade-in
  or fade-out.
- Advanced sound controls can expand the caption with ACE-Step's music planner,
  enable or disable its composition planning, tune planner creativity and
  prompt adherence, set an avoid list and vocal language. Turbo models also
  offer optional 12- or 16-step refinement in place of the recommended
  8-step default.
- Provide lyrics or let Ollama draft sectioned lyrics. ACE-Step receives the
  lyrics and vocal directions, but generated voices and diction are not
  guaranteed to sound fully human or reproduce every word exactly.
- Optionally upload an MP3 (up to 50 MB and 10 minutes) as a style and structure
  reference. ACE-Step uses up to the selected song length to guide generation;
  the original recording is not mixed into the result. Upload only audio you
  have permission to use.
- Download the final MP3 from the result panel.

## Accounts and storage

Guest libraries are temporary and erased when the guest ends the session or
after 20 minutes of inactivity. Closing a browser does not notify the server
immediately, so cleanup occurs on the next expiry sweep. Register an account to
retain songs in a persistent library. The default `user` account must change its
random bootstrap password before accessing the library.

SQLite data and generated files are stored under `backend/data/`,
`backend/generated/`, and `backend/uploads/`; these are local, ignored data
directories. Do not remove them if you want to keep accounts and saved songs.
Use `docker compose down` to stop the services.

## Configuration and remote access

The installer creates `.env` from `.env.example`. `OLLAMA_MODEL`,
`ACE_STEP_MODEL`, `ACE_STEP_QUALITY_MODEL`, `ACE_STEP_LM_MODEL`,
`ACESTEP_OFFLOAD_TO_CPU`, `ACESTEP_OFFLOAD_DIT_TO_CPU`, and
`ACESTEP_LM_OFFLOAD_TO_CPU` select the models and memory settings. The
Compose-published ports bind to localhost. Do not expose the app directly over
plain HTTP; for remote use, place an HTTPS reverse proxy in front of it, keep
`COOKIE_SECURE=true`, and set `CORS_ORIGINS` to the HTTPS origin. Apply rate
limiting at the public proxy.

## Tests

Run the backend checks from this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest -c pytest.ini
```
