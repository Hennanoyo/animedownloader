# ADR-007: Versioned Release Profiles for Discovery and Parsing

## Status

Accepted

## Context

Anime release filenames are not governed by one stable naming convention. Different release groups use different ordering, delimiters, metadata tokens, and episode representations, and a single group may change its convention over time.

The application already has:

- an ephemeral `Release` model returned by the release provider
- a dedicated Nyaa RSS client/parser boundary
- Episode provenance fields such as source, source ID, source title, source URL, and info hash
- a unique Anime + episode-number constraint

The project must therefore discover and interpret external releases without persisting raw search results and without requiring a code deployment every time a known release group's naming convention changes.

## Decision

Use **versioned, declarative release profiles** for known release groups.

A release group has persistent identity and may have two independent kinds of versioned profiles:

- **Parser Profile**: how release titles are interpreted
- **Search Profile**: how Nyaa queries are constructed

Profiles contain ordered declarative rules. Regex patterns are allowed to be stored as data because they must be editable and testable through the Web UI.

The parser architecture is layered:

```
Provider Release
    ↓
Generic Parser
    ↓
Release Group detection
    ↓
Active Group Parser Profile
    ↓
ParsedRelease
```

An unknown group is still processed by the generic parser.

A parser profile is immutable once activated. Changes produce a new draft version that can be tested against representative samples, compared with the active version, and explicitly activated.

Regexes are executed only by a constrained parser engine. The system does not execute arbitrary code stored in the database.

## Version lifecycle

```
draft → active → retired
```

An active profile is never edited in place.

A new naming convention therefore follows:

```
Existing v3
    ↓
new sample/failure observed
    ↓
Draft v4
    ↓
multi-sample validation
    ↓
compare with v3
    ↓
activate v4
    ↓
retire v3
```

The parser version used for a parsed result should be retained when provenance is meaningful.

## Search profiles

Search is also data-driven, but search and parsing are deliberately separate.

A Search Profile may contain ordered query templates using fields such as:

- group
- title
- episode
- resolution
- codec

The discovery service can issue several progressively specific queries, merge the results in memory, and deduplicate them by stable source identity.

This improves recall without coupling parser logic to one exact query format.

## Safety rules

The following are mandatory:

- raw provider search results remain ephemeral
- ambiguous parsing never creates an Episode automatically
- unknown release groups fall back to the generic parser
- regex syntax is validated before activation
- representative multi-sample validation is required before activation
- regex execution is bounded by parser-engine resource limits
- database rules cannot contain executable application code
- same source identity is idempotent
- same episode with a different release is not silently replaced
- ingestion never starts a download
- user-edited Episode metadata is not overwritten by routine re-ingestion

## Consequences

### Positive

- New or changed release naming conventions can be handled without application-code deployment.
- Parser behavior is reproducible through explicit profile versions.
- Web-based validation becomes a safe operational workflow.
- Search strategies can evolve independently from parsing strategies.
- Unknown groups remain discoverable through generic parsing.
- Future release providers can share the same provider → Release → Parse → Match → Ingest architecture.

### Negative

- The system now has configuration and version lifecycle data that must be maintained.
- A parser engine is more complex than a few hard-coded regular expressions.
- Regex execution must be carefully constrained.
- Good profile validation depends on representative release-title samples.

## Out of scope for the initial implementation

- periodic automatic discovery
- automatic downloading
- automatic release ranking/selection
- batch or multi-episode expansion
- movie/special data-model expansion
- additional release providers
