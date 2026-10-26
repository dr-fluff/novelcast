# NovelCast

NovelCast is a self-hosted library for web serials. It downloads chapters for
offline reading, tracks reading progress, and checks followed stories for new
chapters.

## Choose an installation method

| Method | Best for | Start command |
| --- | --- | --- |
| Docker | Always-on or server installation | `docker compose up -d` |
| Managed local install | A personal macOS or Linux machine | `./install` |
| Local development | Working on NovelCast itself | `make dev` |

## Docker installation

Use Docker for a persistent installation on a desktop, NAS, or server. Docker
must be installed and running first.

```bash
git clone https://github.com/dr-fluff/novelcast.git
cd novelcast
cp .env.example .env
docker compose up -d --build
```

Before exposing Docker outside your own machine, replace `SECRET_KEY` in
`.env` with a long random value.

Open <http://127.0.0.1:8000>. The containers restart automatically unless
explicitly stopped. Your database, books, configuration, and logs remain in
the repository's `data/`, `config/`, and `logs/` directories.

Useful Docker commands:

```bash
docker compose ps                 # service status
docker compose logs -f novelcast  # live logs
docker compose down               # stop it
```

To update a Docker installation:

```bash
git pull --ff-only
docker compose up -d --build
```

## Managed local installation

This option runs NovelCast as a per-user background service without Docker.
It supports macOS (`launchd`) and Linux (`systemd --user`). You need Git,
Python 3.11+, and `curl`.

```bash
git clone https://github.com/dr-fluff/novelcast.git
cd novelcast
./install
```

The installer creates a production `.env` when one is missing, installs locked
dependencies, applies database migrations, and starts the service. It uses
<http://127.0.0.1:8000> by default.

Manage the service with:

```bash
./scripts/service.sh status
./scripts/service.sh start
./scripts/service.sh restart
./scripts/service.sh stop
```

Update a managed local installation with:

```bash
./update
```

This performs a fast-forward-only Git update, installs locked dependencies,
applies migrations, and restarts the service. It never changes `data/` or
`config/`, and refuses to overwrite tracked local edits.

## Local development

Use this mode when changing the application. It runs the FastAPI backend on
port `8001` and BrowserSync on port `3000`.

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node.js 18+.

```bash
git clone https://github.com/dr-fluff/novelcast.git
cd novelcast
cp .env.example .env
uv sync
npm install
make dev
```

Open <http://127.0.0.1:3000>. The backend is also directly available at
<http://127.0.0.1:8001>.

Common development commands:

```bash
make backend  # backend only
make frontend # BrowserSync only
make lint     # Ruff checks
make test     # test suite
```

## Configuration and data

`.env` contains runtime settings. Start from `.env.example` for Docker or
development. The managed installer creates an equivalent production file
automatically. Keep `.env`, `data/`, and `config/` private: they can contain
your library, credentials, and application state.

Administrators see a banner when a newer GitHub release is available. It checks
`GITHUB_REPOSITORY` (default: `dr-fluff/novelcast`) at most once every six
hours; set that value to an empty string to disable release checks.

Managed local installs bind to localhost by default. Docker publishes port
`8000` according to Docker's host defaults; to restrict it to localhost, change
the Compose port mapping to `127.0.0.1:8000:8000`. If you expose NovelCast on
a network, set a strong `SECRET_KEY` and use a reverse proxy with HTTPS.
