# Frontend Agent Instructions

## Stack

- Vite
- React
- TypeScript
- pnpm
- SCSS Modules
- React Aria Components (RAC)
- React Aria / React Stately for lower-level interaction cases
- Feature-Sliced Design (FSD)
- TanStack Query v5
- TanStack Router v1
- TanStack Form v1
- Zod
- hls.js
- dash.js
- JASSUB

## Architecture Rules

- Keep `web/apps` and `web/libs` boundaries intact.
- Organize application code with FSD layers: `app`, `pages`, `widgets`, `features`, `entities`, and `shared`.
- Keep UI logic close to the FSD slice that owns the behavior.
- Reusable UI belongs in `web/libs`, not inside a single application.
- Prefer SCSS Modules for component and page styling. Keep global styles to the minimum required application shell/reset, expressed through SCSS module `:global` selectors.
- Prefer React Aria Components for accessible UI primitives and composite controls.
- For interactions requiring deeper behavioral/state customization than RAC exposes, use React Aria hooks or React Stately rather than hand-rolled accessibility state machines.
- Use TanStack Router v1 for client routing and URL state. Prefer type-safe route search schemas with Zod.
- Use TanStack Query v5 for server state, request caching, invalidation, cancellation, and loading/error state. Do not scatter raw fetch calls across components.
- Use TanStack Form v1 for non-trivial forms and validation workflows. Use Zod schemas for runtime validation where input or API data must be trusted.
- Keep API access behind the reusable `shared/api` client and feature/entity API modules.
- Keep media engine logic separate from player UI.
- HLS/DASH implementation details should be hidden behind media-engine abstractions where practical.
- JASSUB subtitle rendering is a dedicated media concern and should not be embedded into unrelated UI components.

## Testing

Use the repository's pnpm/just commands when available. At minimum, keep linting, type checking, unit tests, and relevant E2E tests passing before completing a change.
