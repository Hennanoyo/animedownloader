default:
  @just --list

up:
  docker compose up --build

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

storage-media-smoke-gpu episode_id timeout="900":
  @encoder="$(docker compose -f compose.yaml -f compose.gpu.yaml exec -T worker sh -c 'printf %s "$FFMPEG_VIDEO_ENCODER"')"; \
  hwaccel="$(docker compose -f compose.yaml -f compose.gpu.yaml exec -T worker sh -c 'printf %s "$FFMPEG_HWACCEL"')"; \
  test "$encoder" = "hevc_nvenc" && test "$hwaccel" = "cuda" || { \
    echo "GPU worker is not active with NVENC/CUDA. Run 'just up-gpu' first."; \
    exit 1; \
  }; \
  docker compose -f compose.yaml -f compose.gpu.yaml exec -T worker uv run --package animedownloader-worker python3 /app/scripts/storage-media-smoke.py {{episode_id}} --timeout {{timeout}}

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
