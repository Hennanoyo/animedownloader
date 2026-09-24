default:
  @just --list

up:
  @if command -v nvidia-smi >/dev/null 2>&1 && docker compose -f compose.yaml -f compose.gpu.yaml run --rm --no-deps --build --entrypoint sh worker -c 'nvidia-smi >/dev/null 2>&1'; then \
    echo "[up] NVIDIA GPU is available; starting GPU-enabled worker."; \
    docker compose -f compose.yaml -f compose.gpu.yaml up --build; \
  else \
    echo "[up] NVIDIA GPU is unavailable; starting CPU worker."; \
    docker compose up --build; \
  fi

up-gpu:
  docker compose -f compose.yaml -f compose.gpu.yaml up --build

gpu-check:
  docker compose -f compose.yaml -f compose.gpu.yaml run --rm --no-deps --entrypoint sh worker -c 'nvidia-smi && ffmpeg -hide_banner -hwaccels | grep -Fx cuda && ffmpeg -hide_banner -encoders | grep -F hevc_nvenc'

down:
  docker compose down

down-v:
  docker compose down -v

logs service="":
  docker compose logs -f {{service}}

media-smoke episode_id timeout="180":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/media-streaming-smoke.py {{episode_id}} --timeout {{timeout}}

storage-smoke:
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/storage-smoke.py

storage-media-smoke episode_id timeout="1800":
  docker compose exec -T worker uv run --package animedownloader-worker python3 /app/scripts/storage-media-smoke.py {{episode_id}} --timeout {{timeout}}

storage-media-smoke-gpu episode_id timeout="1800":
  @echo "[storage-media-smoke-gpu] compatibility alias; encoder selection is automatic."
  just storage-media-smoke {{episode_id}} {{timeout}}

web-install:
  cd web && pnpm install

web-format:
  cd web && pnpm format

web-check:
  cd web && pnpm lint && pnpm typecheck && pnpm test

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
