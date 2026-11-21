# Local Song Generator

A Dockerized song-generation starter that uses an optional locally hosted Ollama model for lyrics and keeps generated projects on the machine.

## Install and run

Install Docker Compose and configure the NVIDIA Container Toolkit for the ACE-Step GPU service. Then, from the project directory:

```bash
./install.sh
./run.sh
```

`install.sh` builds the application containers, downloads the default Ollama model (`llama3.2`), and initializes the ACE-Step checkpoint. It then stops the containers; models remain in Docker volumes. This may take a while and requires an NVIDIA GPU supported by Docker.

`run.sh` starts the containers and prints the application and API URLs. Open http://localhost:5173 to generate songs. The API documentation is at http://localhost:8000/docs. Stop the containers with `docker compose down`.

The installer creates `.env` from `.env.example` if needed. You can set `OLLAMA_MODEL` in `.env` to select another Ollama model before running `./install.sh`.

## Local model behavior

- When Ollama is reachable, it generates a title and sectioned lyrics.
- When Ollama is not reachable, the application returns a deterministic sample arrangement so the UI and audio pipeline remain usable.
- The MVP synthesizes a local instrumental arrangement and encodes it as MP3. Set `MUSIC_API_URL` to an HTTP music-generation service that accepts a JSON prompt and returns audio bytes to replace the demo synthesizer.
## Audio

Each completed song includes:

- Browser-playable MP3 audio
- A downloadable MP3 file
- A WAV source file
- A generated arrangement containing drums, bass, a synth pad, and a lead melody

