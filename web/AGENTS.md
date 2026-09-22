# Frontend Agent Instructions

## Stack

- Vite
- React
- TypeScript
- pnpm
- TanStack Query v5
- TanStack Router v1
- TanStack Form v1
- Zod
- hls.js
- dash.js
- JASSUB

## Rules

- Keep `web/apps` and `web/libs` boundaries intact.
- Prefer strict TypeScript types; avoid `any` unless there is a documented reason.
- Keep API access behind a reusable API/client layer rather than scattering fetch logic across components.
- Keep media engine logic separate from player UI.
- HLS/DASH implementation details should be hidden behind media-engine abstractions where practical.
- JASSUB subtitle rendering is a dedicated media concern and should not be embedded into unrelated UI components.
- Reusable UI belongs in `web/libs`, not inside a single application.

## Testing

Use the repository's pnpm/just commands when available. At minimum, keep linting, type checking, unit tests, and relevant E2E tests passing before completing a change.
