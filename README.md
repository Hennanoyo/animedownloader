# AnimeDownloader

AnimeDownloader is a pnpm + uv monorepo for downloading anime releases and preparing browser-oriented streaming media.

## Repository

- `web/`: React/Vite frontend workspace
- `server/`: Python/FastAPI/Taskiq backend workspace
- `docs/`: architecture and development documentation
- `compose.yaml`: local development stack

## Development

The supported environment is WSL2 Ubuntu + Docker Desktop + VSCode Dev Containers.

Clone the repository from WSL2:

```bash
git clone https://github.com/Hennanoyo/animedownloader.git
cd animedownloader
code .
```

Then use **Dev Containers: Reopen in Container**.

The Dev Container attaches to the `api` service and starts the full Compose stack automatically.

See [`docs/development.md`](docs/development.md) for first-time setup, environment variables, branch usage, and service URLs.

## Checks

```bash
just check
```

GitHub Actions runs the project quality checks and validates the Compose configuration.

## Architecture

See:

- `AGENTS.md`
- `docs/architecture/overview.md`
- `docs/architecture/media-pipeline.md`
- `docs/architecture/subtitles.md`
- `docs/architecture/storage.md`
- `docs/decisions/`

## Media

The project targets HEVC as its primary video codec, reuses shared CMAF/fMP4 assets between HLS and DASH where practical, and normalizes non-ASS subtitles for JASSUB.

## Initial Scope

Feature work is implemented incrementally:

1. Nyaa RSS search
2. Download job and progress model
3. Torrent downloader
4. Media inspection
5. Subtitle normalization
6. HEVC transcoding/package pipeline
7. CMAF/HLS/DASH packaging
8. SeaweedFS storage
9. Web media player and JASSUB integration
10. Thumbnail timeline
