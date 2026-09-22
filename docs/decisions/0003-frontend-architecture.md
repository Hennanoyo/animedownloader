# 0003 Frontend architecture

## Status

Accepted

## Context

The frontend will grow from release search into download management, media inspection, playback, subtitles, and timeline tooling. A consistent application structure is needed before those features expand.

## Decision

The web application follows these conventions:

- SCSS Modules are the default styling mechanism.
- React Aria Components are the default accessible UI primitives.
- React Aria and React Stately are used when a lower-level interaction or state model is required.
- Feature-Sliced Design separates app, pages, widgets, features, entities, and shared concerns.
- TanStack Router v1 owns routing and URL search state.
- TanStack Query v5 owns server state and request caching.
- TanStack Form v1 and Zod are used for non-trivial forms and runtime validation.

These choices are conventions rather than requirements to use every library in every component. The simplest suitable abstraction should be preferred.

## First feature slice

Release search uses:

Browser → TanStack Router search params → TanStack Form + Zod → API client → FastAPI → Nyaa RSS → typed release data → TanStack Query cache → FSD release list.
