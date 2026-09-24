# Development

## Supported Environment

The supported development environment is:

- Windows host
- WSL2 Ubuntu
- Docker Desktop with WSL integration
- VSCode
- VSCode Dev Containers extension
- Docker Compose

The repository uses a dedicated development container containing both Node.js/pnpm and Python/uv. Runtime services remain separate Compose containers.

## Clone and Open

Clone the repository from WSL2 Ubuntu:

```bash
git clone https://github.com/Hennanoyo/animedownloader.git
cd animedownloader
code .
```

In VSCode, run **Dev Containers: Reopen in Container**.

The Dev Container now includes the GPU Compose override. On this development machine, rebuilding the Dev Container therefore gives the Worker NVIDIA GPU access without requiring `just up`. The application still falls back to CPU encoding when NVENC is unavailable.

The Dev Container configuration uses:

- `dev`: development shell with Node.js 24, pnpm, Python 3.14, and uv
- `api`: FastAPI runtime/development service
- `web`: Vite development server
- `worker`: Taskiq worker
- `db`: PostgreSQL
- `redis`: Redis
- `storage`: SeaweedFS Filer

VSCode attaches to the `dev` container. The full Compose stack is started automatically.

The repository is mounted at `/app`.

Normally, work starts from the default `main` branch:

```bash
git fetch origin
git switch main
```

Feature work should use focused branches such as `feature/release-catalog`.

## First Setup

The Dev Container runs dependency setup automatically with locked dependency resolution:

- `uv sync --all-packages --locked --project /app/server`
- `pnpm install --frozen-lockfile` in `/app/web`

The Dev Container keeps the Python environment under `/home/node/.venvs/animedownloader-server` and the pnpm store under `/home/node/.cache/pnpm/store`. These paths are outside the repository, so opening the container does not modify dependency caches in the working tree.

When dependencies change, regenerate and commit the corresponding lockfile, then rebuild/reopen the Dev Container.

The runtime `api` and `worker` services also use locked uv installs. This prevents their bind-mounted workspace from rewriting `server/uv.lock` during startup.

Backend environment overrides are optional. When needed:

```bash
cp /app/server/.env.example /app/server/.env
```

The Worker reads `QBITTORRENT_API_KEY` from `server/.env`. The qBittorrent WebUI is only needed to generate the API key; the application does not use the WebUI for download execution.

Do not commit `server/.env`.

## Frontend Conventions

The frontend follows the conventions in `web/AGENTS.md` and `docs/decisions/0003-frontend-architecture.md`:

- SCSS Modules for component and page styles
- React Aria Components for accessible UI primitives
- React Aria / React Stately for lower-level interaction behavior when needed
- Feature-Sliced Design for application structure
- TanStack Router v1 for routing and URL state
- TanStack Query v5 for server state
- TanStack Form v1 + Zod for non-trivial forms and validation

The first feature slice exposes Nyaa RSS release search through the API and URL-addressable search state.

## Local URLs

- Frontend: `http://localhost:5173` (Vite)
- API: `http://localhost:8000`
- API health: `http://localhost:8000/api/health`
- SeaweedFS Filer: `http://localhost:8888`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Browser Media Access

The development SeaweedFS Filer is exposed directly to the browser as the public media endpoint. Its CORS allowlist includes the Vite development origins (`http://localhost:5173` and `http://127.0.0.1:5173`) so MP4, HLS/DASH manifests, segments, subtitles, and fonts can be fetched by the player.

If the frontend origin or public media endpoint changes, update the Filer's `-allowedOrigins` setting in `compose.yaml` together with `STORAGE_PUBLIC_URL`.

## Running and Debugging

The `api`, `web`, and `worker` processes are started by Docker Compose.

Use the integrated VSCode terminal in the `dev` container for repository commands:

```bash
just check
```

Use Docker Desktop or the Compose output panel to inspect service logs.

Because Docker Compose is managed by the Dev Containers extension in the supported workflow, do not assume the `dev` container needs access to the host Docker socket.

To verify GPU access from the repository environment:

```bash
just gpu-check
```

This checks NVIDIA visibility and performs a real `hevc_nvenc` encode probe.

## Runtime Media Storage Smoke Test

The storage migration can be validated against the real Compose SeaweedFS service without adding live media workflows to CI.

`STORAGE_BACKEND` defaults to `local`. To exercise the SeaweedFS application path, start or restart the API and Worker with the backend selected:

```bash
STORAGE_BACKEND=seaweedfs docker compose up -d --build api worker
```

Process a new Episode while this backend is active. Existing derived artifacts written before the switch remain in local storage and are not migrated automatically.

Then run the adapter check and the end-to-end media storage check:

```bash
just storage-smoke
just storage-media-smoke <episode-id>
```

`storage-media-smoke` validates the pipeline after the Episode's download has completed. It reconciles and enqueues missing downstream media-processing, preparation, subtitle/attachment, and streaming-packaging work, waits for the pipeline to settle, then materializes derived objects from the configured storage backend, validates the stored playable MP4 with FFprobe, and verifies thumbnails, subtitles, attachments/fonts, HLS/DASH manifests, and CMAF segments.

For a true Episode-ID-only end-to-end test, use:

```bash
just reset-dev
STORAGE_BACKEND=seaweedfs just up
just media-e2e-smoke <episode-id>
```

Use `just up` rather than plain `docker compose up` when GPU acceleration should be available. `just up` tests NVIDIA access from the GPU-enabled Compose worker before choosing the GPU or CPU stack. If Docker cannot expose the NVIDIA runtime, it reports that explicitly and falls back to the CPU worker. Use `just gpu-check` to inspect GPU access directly, or `just up-gpu` to require the GPU Compose configuration.

The `media-e2e-smoke` command creates a download job when needed, waits for the Torrent download to complete, then invokes `storage-media-smoke` for the complete downstream media pipeline. It is intended for local/development validation and may perform a real torrent download, so it is not part of normal CI.

The `--timeout` value applies to the download stage and each downstream media stage:

```bash
just media-e2e-smoke <episode-id> 3600
```

Use `--skip-playable` when a full playable-file download is undesirable:


```bash
docker compose exec -T worker uv run --package animedownloader-worker \
  python3 /app/scripts/storage-media-smoke.py <episode-id> --skip-playable
```

## Development Data Reset

`reset-dev` is intentionally destructive. It stops Compose and removes all Compose-managed development volumes, including PostgreSQL, Redis, SeaweedFS, downloads, media, and qBittorrent state.

Use it when storage rules or database schemas have changed and old development data should not be migrated:

```bash
just reset-dev
```

After the reset, start the stack again. For the media storage E2E workflow, use SeaweedFS explicitly:

```bash
STORAGE_BACKEND=seaweedfs just up
```

## Monorepo

The repository contains two package-management domains:

- `web/`: pnpm workspace
- `server/`: uv workspace

The frontend application currently lives at `web/apps/web`.

The backend workspace currently contains:

- `server/apps/api`
- `server/apps/worker`
- `server/domains/releases`
- `server/libs/config`
- `server/libs/nyaa`

The `domains` layer contains business/domain behavior, while `libs` contains reusable technical adapters.

## Lockfiles

Lockfiles are source-controlled artifacts.

When dependencies are added or changed, regenerate the appropriate workspace lockfile and commit it with the dependency change:

- `web/pnpm-lock.yaml`
- `server/uv.lock`

CI and the runtime containers use locked installs.

## CI Philosophy

GitHub Actions is the deterministic verification layer.

AI-assisted development should follow:

1. Inspect the repository and relevant documentation.
2. Implement a focused change.
3. Run focused local checks.
4. Commit and push through the normal branch workflow.
5. Let GitHub Actions run the applicable checks.
6. Inspect failed job logs.
7. Fix the root cause.
8. Re-run verification.

CI should not depend on live torrent downloads or large real-world media files.

Use small fixtures for media integration/smoke tests and deterministic fixtures for external protocols.
