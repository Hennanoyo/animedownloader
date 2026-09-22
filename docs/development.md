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

To work on the current bootstrap PR before it is merged:

```bash
git fetch origin
git switch feature/bootstrap
```

Normally, after the bootstrap is merged, use the default `main` branch.

## First Setup

The Dev Container runs the initial dependency setup automatically:

- `uv sync --all-packages --project /app/server`
- `pnpm install` in `/app/web`

You can repeat either command manually when dependencies change.

Backend environment overrides are optional. When needed:

```bash
cp /app/server/.env.example /app/server/.env
```

Do not commit `server/.env`.

## Local URLs

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/api/health`
- SeaweedFS Filer: `http://localhost:8888`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Running and Debugging

The `api`, `web`, and `worker` processes are started by Docker Compose.

Use the integrated VSCode terminal in the `dev` container for repository commands:

```bash
just check
```

Use Docker Desktop or the Compose output panel to inspect service logs.

Because Docker Compose is managed by the Dev Containers extension in the supported workflow, do not assume the `dev` container needs access to the host Docker socket.

## Monorepo

The repository contains two package-management domains:

- `web/`: pnpm workspace
- `server/`: uv workspace

The frontend application currently lives at `web/apps/web`.

The backend workspace currently contains:

- `server/apps/api`
- `server/apps/worker`
- `server/libs/config`

The `server/domains` layer is reserved for domain packages introduced as features are implemented.

## Lockfiles

Lockfiles are source-controlled artifacts.

When dependencies are added or changed, regenerate the appropriate workspace lockfile and commit it with the dependency change:

- `web/pnpm-lock.yaml`
- `server/uv.lock`

The initial CI workflow temporarily falls back to non-frozen dependency resolution when a lockfile does not yet exist. Once the initial lockfiles are committed, CI should use locked installs exclusively.

## CI Philosophy

GitHub Actions is the deterministic verification layer.

AI-assisted development should follow:

1. Inspect the repository and relevant documentation.
2. Implement a focused change.
3. Run focused local checks.
4. Commit/push through the normal branch workflow.
5. Let GitHub Actions run the applicable checks.
6. Inspect failed job logs.
7. Fix the root cause.
8. Re-run verification.

CI should not depend on live torrent downloads or large real-world media files.

Use small fixtures for media integration/smoke tests and deterministic fixtures for external protocols.
