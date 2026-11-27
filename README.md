# Local Song Generator

## Open in browser
http://localhost:5173

A self-hosted song studio with temporary guest sessions, persistent user
libraries, AI-written lyrics, and ACE-Step audio generation.

## Install and run

Requirements: Docker Compose, an NVIDIA GPU with the NVIDIA Container Toolkit,
and enough disk space for model weights. ACE-Step Turbo is selected by default.
The default configuration runs the 0.6B music planner on the CPU and offloads
the diffusion model (DiT) to reduce GPU memory use. For faster Turbo generation
on a GPU with enough free memory, set these values in `.env`:

```dotenv
ACESTEP_LM_DEVICE=cuda
ACESTEP_LM_BACKEND=pt
ACESTEP_LM_OFFLOAD_TO_CPU=false
ACESTEP_OFFLOAD_DIT_TO_CPU=false
ACESTEP_NO_INIT=false
```

Apply the settings with `docker compose up -d --no-deps --wait ace-step` when the
generation queue is empty. ACE-Step loads the default model and PyTorch planner
at startup. Selecting a different checkpoint still takes time to load it. If
GPU memory runs short, especially with XL checkpoints, restore the CPU settings
from `.env.example`, remove `ACESTEP_NO_INIT`, and recreate ACE-Step.

```bash
./install.sh
./run.sh
```

The installer creates `.env` if needed, runs `./pull.sh`, and builds the app.
It prints the one-time password for the default `user` account on first setup.
Change it at first login.

Use `./pull.sh` to pull the ACE-Step and Ollama images together with the
studio checkpoints, audio decoder, and configured Ollama lyrics model.
Docker's image-only pull commands fetch image layers. The project script
also fills the persistent model volumes and checks for missing checkpoint
shards. A fresh pull needs several dozen gigabytes of model storage. Cached
checkpoints are reused on subsequent pulls.

Open `http://<server-ip>:5173` in a browser on your network (for this machine,
`http://172.23.42.239:5173`). Sign in, create an account, or choose **Continue
as guest**. The API documentation is at
[http://localhost:8000/docs](http://localhost:8000/docs).

The song description field links to the same host and port used to open the
studio, so the link works from other devices on your network too.

### YuE2 worker (experimental)

YuE2 runs as a separate, low-VRAM worker. A short test song completed on an
RTX 5080 with 16 GiB VRAM, but took about 50 seconds and generated 38.9 seconds
of audio. Requested-length behavior and longer songs still need validation
before YuE2 is enabled in the model picker. Weights are downloaded into
persistent Docker volumes by the project pull script. YuE2 weights are licensed
CC BY-NC 4.0; commercial use requires a separate license from the authors.

```bash
./pull.sh --yue2
docker compose --profile yue2 up -d --build
```

### MiniMax Music 3

For local MiniMax Music 3 generation, enable the `minimax` Compose profile.
The worker uses ComfyUI's INT8 package to reduce memory use. The weights take
about 11 GiB of disk space. Generation can take several minutes depending on
song length and available GPU memory. The worker uses PyTorch with CUDA 13
and needs a compatible NVIDIA driver.

```bash
./pull.sh --minimax
docker compose --profile minimax up -d --build
```

Set `COMPOSE_PROFILES=minimax` in `.env` to include the worker in future runs
and pulls. Refresh the studio after it starts and choose **MiniMax Music 3** in
the generation model menu. It uses the description and lyrics and can end
before the selected length. Select an ACE-Step model for MP3 references.
On a shared GPU, `ACESTEP_OFFLOAD_DIT_TO_CPU=true` trades some ACE-Step speed
for more free GPU memory while MiniMax runs. The MiniMax worker releases each
stage's model from GPU memory as it moves from encoding to sampling to decoding.

## Using the studio

- Describe the song in plain language. Include any mood, tempo, meter, or
  vocal details you want in the description. Genre, key, and instruments can
  also be selected in the form.
- Choose a song length from 30 seconds to 2 minutes.
- Choose among ACE-Step models: **Turbo Lite** for the fastest path (2B Turbo
  without the 0.6B composition planner), **Turbo** for fast generation with
  planning,
  **Turbo Shift1** for more detail with looser prompt matching,
  **Turbo Shift3** for clearer timbre, **SFT** for more detail and prompt
  guidance, **XL Turbo** for a larger model at Turbo speed, or **XL SFT** for
  the most detailed slower option. XL models need more GPU memory.
- Use the **Composition planner** toggle to trade generation time for more
  arrangement guidance. Turbo models use eight diffusion steps, and SFT models
  use 50.
- Choose a vocal preset for the singer's delivery or chorus harmonies, or
  select **Instrumental** for a song without lyrics. Provide lyrics or let Ollama draft
  sectioned lyrics in the selected language. Vocal presets guide ACE-Step's
  performance and can vary between takes.
- For a single singer with audible breaths and less doubling, select
  **Natural lead**. Try it with **XL SFT** for detailed studio takes or
  **XL Turbo** for faster auditions. Leave space between lyric lines and
  keep the accompaniment sparse if you want the voice up front.
- Optionally upload an MP3 (up to 50 MB and 10 minutes) as a style and structure
  reference. ACE-Step uses up to the selected song length to guide generation;
  the default 70% reference strength keeps more of its sound and structure,
  while lower values give the text description more freedom. The original
  recording is not mixed into the result. Upload only audio you have permission
  to use.
- **Studio master** is enabled by default in the form for loudness
  normalization, a 24-bit WAV, and a 320 kbps MP3. Download either format
  in the result panel.
- To compare the bundled decoder with ScragVAE, set
  `ACESTEP_VAE_CHECKPOINT=scragvae` in `.env`, run `./pull.sh`, then recreate
  ACE-Step. Restore `official` to switch back.

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

For free public HTTPS access without router port forwarding, enable the
`public` Compose profile alongside any model profiles in `.env`:

```dotenv
COMPOSE_PROFILES=minimax,public
```

Run `./run.sh`, then `./public-url.sh` to print the current HTTPS link. The
description link in the studio uses that same hostname. This uses Cloudflare's
free Quick Tunnel: the address changes when the tunnel restarts and has no
uptime guarantee. A permanent custom domain requires registering a name and
configuring a named tunnel or another public HTTPS endpoint.

The installer creates `.env` from `.env.example`. `OLLAMA_MODEL`,
`ACE_STEP_MODEL`, `ACE_STEP_QUALITY_MODEL`, `ACE_STEP_LM_MODEL`,
`ACESTEP_OFFLOAD_TO_CPU`, `ACESTEP_OFFLOAD_DIT_TO_CPU`, and
`ACESTEP_LM_OFFLOAD_TO_CPU` select the models and memory settings. The
Compose-published app ports bind to localhost. Keep `COOKIE_SECURE=true` for
public access. The frontend proxies API calls on the same origin, so the public
tunnel does not require an extra CORS origin.

## Tests

Run the backend checks from this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest -c pytest.ini
```
