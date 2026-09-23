default:
  @just --list

up:
  docker compose up --build

down:
  docker compose down

down-v:
  docker compose down -v

logs service="":
  docker compose logs -f {{service}}

web-install:
  cd web && pnpm install

web-check:
  cd web && pnpm lint && pnpm typecheck && pnpm test

server-sync:
  cd server && uv sync --all-packages

server-format:
  cd server && uv run ruff format .

format: server-format

server-check:
  cd server && uv run ruff check .
  cd server && uv run ruff format --check .
  cd server && uv run pyright
  cd server && uv run pytest

check: web-check server-check
