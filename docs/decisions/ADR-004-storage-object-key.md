# ADR-004: Persist Storage Object Keys Instead of Public URLs

## Status

Accepted

## Context

The same application must work in local Docker Compose environments and deployed environments where storage endpoints and reverse-proxy domains differ.

## Decision

Store storage object keys as the canonical reference in PostgreSQL.

Derive public/browser-facing URLs at the API boundary from environment-backed configuration.

Keep SeaweedFS client details behind a storage abstraction.

## Consequences

- Database data is independent of deployment URLs.
- Storage endpoints can change without rewriting media metadata rows.
- Access control or signed URL delivery can be introduced later without changing the stored object identity.
