# Development

## Environment

The supported development environment is:

- Windows host
- WSL2 Ubuntu
- Docker Desktop with WSL integration
- VSCode
- VSCode Dev Containers extension
- Docker Compose

Development and application processes are intended to run inside the Dev Container/Compose environment.

## Clone and Open

Clone the repository from WSL2 Ubuntu:

```bash
git clone https://github.com/Hennanoyo/animedownloader.git
cd animedownloader
code .
```

In VSCode, run **Dev Containers: Reopen in Container**.

The repository's `.devcontainer/devcontainer.json` attaches VSCode to the `api` service and starts the complete Compose stack:

- `api`
- `web`
- `worker`
- `db`
- `redis`
- `storage`

The repository is mounted at `/app` inside the container.

To work on the current bootstrap PR before it is merged:

```bash
git fetch origin
git switch feature/bootstrap
```

Normally, after the bootstrap is merged, use the default `main` branch.

## First Setup

Open a terminal in the Dev Container.

Frontend dependencies:

```bash
cd /app/web
pnpm install
```

Backend dependencies:

```bash
cd /app/server
uv sync --all-packages
```

Copy backend environment defaults when local overrides are needed:

```bash
cp /app/server/.env.example /app/server/.env
```

The default Compose environment values are already supplied by `compose.yaml`.

Do not commit `server/.env`.

## Local URLs

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/api/health`
- SeaweedFS Filer: `http://localhost:8888`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Daily Development

The root `justfile` provides common repository checks:

```bash
just check
```

Because Docker Compose is managed by the Dev Containers extension in the supported workflow, use the VSCode/Dev Containers commands to start and stop the stack rather than assuming Docker CLI access inside the application container.

Service logs can be viewed from Docker Desktop or the Dev Containers/Compose output.

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
