default:
  @just --list

up:
  @if ! command -v nvidia-smi >/dev/null 2>&1; then     echo "[up] Host NVIDIA tooling is unavailable; starting CPU worker.";     docker compose up --build;   elif docker compose -f compose.yaml -f compose.gpu.yaml run --rm --no-deps --build --entrypoint sh worker -c 'nvidia-smi >/dev/null 2>&1'; then     echo "[up] NVIDIA GPU is available to Docker; starting GPU-enabled worker.";     docker compose -f compose.yaml -f compose.gpu.yaml up --build;   else     echo "[up] Host NVIDIA tooling is present, but Docker cannot access the GPU.";     echo "[up] Run 'just gpu-check' to inspect the NVIDIA runtime; starting CPU worker.";     docker compose up --build;   fi

up-gpu:
  docker compose -f compose.yaml -f compose.gpu.yaml up --build

gpu-check:
  docker compose -f compose.yaml -f compose.gpu.yaml run --rm --no-deps --build --entrypoint sh worker -c 'nvidia-smi && ffmpeg -hide_banner -encoders | grep -F hevc_nvenc && ffmpeg -hide_banner -v error -f lavfi -i testsrc2=size=1920x1080:rate=1 -frames:v 2 -an -c:v hevc_nvenc -preset p5 -rc vbr -cq 28 -b:v 0 -pix_fmt yuv420p -f null -'

down:
  docker compose down

down-v:
  docker compose down -v

reset-dev:
  @echo "[reset-dev] WARNING: removing all development Compose volumes."
  @echo "[reset-dev] This deletes PostgreSQL, Redis, SeaweedFS, downloads, media, and qBittorrent state."
  docker compose down -v --remove-orphans

logs service="":
  docker compose logs -f {{service}}

media-smoke episode_id timeout="180":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/media-streaming-smoke.py {{episode_id}} --timeout {{timeout}}

media-repackage episode_id timeout="1800":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/media-repackage.py {{episode_id}} --timeout {{timeout}}

storage-smoke:
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/storage-smoke.py

storage-media-smoke episode_id timeout="1800":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/storage-media-smoke.py {{episode_id}} --timeout {{timeout}}

media-e2e-smoke episode_id timeout="3600":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/media-e2e-smoke.py {{episode_id}} --timeout {{timeout}}

storage-media-smoke-gpu episode_id timeout="1800":
  @echo "[storage-media-smoke-gpu] compatibility alias; encoder selection is automatic."
  just storage-media-smoke {{episode_id}} {{timeout}}

web-install:
  cd web && pnpm install

web-format:
  cd web && pnpm format

web-check:
  cd web && pnpm lint && pnpm typecheck && pnpm test

web-browser-install:
  cd web && pnpm exec playwright install chromium

web-browser-check:
  cd web && pnpm exec tsc --noEmit -p e2e/tsconfig.json
  cd web && pnpm run e2e -- --project=chromium

real-playback-smoke episode_id base_url="http://localhost:5173":
  cd web && REAL_PLAYBACK_EPISODE_ID={{episode_id}} PLAYWRIGHT_TEST_BASE_URL={{base_url}} PLAYWRIGHT_SKIP_WEB_SERVER=1 pnpm run e2e:real -- --project=chromium

server-sync:
  cd server && uv sync --all-packages

server-format:
  cd server && uv run ruff format .

format: web-format server-format

server-check:
  cd server && uv run ruff check .
  cd server && uv run ruff format --check .
  cd server && uv run pyright
  cd server && uv run pytest

check: web-check server-check
