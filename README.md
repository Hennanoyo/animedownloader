# AnimeDownloader

AnimeDownloader is a pnpm + uv monorepo for downloading anime releases and preparing browser-oriented streaming media.

## Repository

- `web/`: React/Vite frontend workspace
- `server/`: Python/FastAPI/Taskiq backend workspace
- `docs/`: architecture and development documentation
- `compose.yaml`: local development stack

## Development

The intended environment is WSL2 Ubuntu with VSCode Dev Containers and Docker Compose.

Start the stack:

```bash
just up
```

The frontend is available at `http://localhost:5173` and the API at `http://localhost:8000/api/health`.

The first dependency install may create workspace lockfiles. Commit those lockfiles once generated.

## Checks

```bash
just check
```

GitHub Actions runs the same project-level quality checks and validates the Compose configuration.

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

The current repository contains only the development foundation. Feature work will be implemented incrementally:

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
