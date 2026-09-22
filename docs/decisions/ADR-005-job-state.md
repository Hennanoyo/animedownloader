# ADR-005: Separate Durable Job State from Transient Events

## Status

Accepted

## Context

Downloads and media processing are long-running operations. Browsers can disconnect and workers can restart, so transient progress messages alone are insufficient.

## Decision

Persist authoritative job state in PostgreSQL.

Use Taskiq for job execution.

Use Redis for transient progress/events when required.

A browser must be able to reconnect and recover current job state from the API even if it missed realtime events.

## Consequences

- Job status survives browser reconnects and worker restarts.
- Realtime delivery remains lightweight and transient.
- Job state transitions must be explicit and idempotency/retry behavior must be designed as implementation proceeds.
