# Song Generator

Install Docker Compose and configure the NVIDIA Container Toolkit for the ACE-Step GPU service. Then, from the project directory:

```bash
./install.sh
./run.sh
```

`install.sh` builds the application containers, downloads the default Ollama model (`llama3.2`), and initializes the ACE-Step checkpoint. It then stops the containers; models remain in Docker volumes. This may take a while and requires an NVIDIA GPU supported by Docker.

`run.sh` starts the containers and prints the application and API URLs. Open http://localhost:5173 to generate songs. The API documentation is at http://localhost:8000/docs. Stop the containers with `docker compose down`.

The installer creates `.env` from `.env.example` if needed. You can set `OLLAMA_MODEL` in `.env` to select another Ollama model before running `./install.sh`.
