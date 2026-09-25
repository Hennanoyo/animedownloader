# Release Discovery & Episode Ingestion

## Goal

Turn external release search results into safe, reviewable Episode candidates without persisting raw release-search results or coupling discovery to downloading.

The release-discovery pipeline is intentionally separated into four concerns:

```
Provider → Release → Parse → Match → Ingest
```

- **Provider** fetches external search results.
- **Release** is a provider-neutral, ephemeral representation of one external release.
- **Parse** derives structured metadata from the release title using generic rules plus optional release-group-specific profiles.
- **Match** determines whether the parsed release maps unambiguously to an existing Anime.
- **Ingest** performs an explicit, transactional Episode create/update operation after user acceptance.

## Core data flow

```
Nyaa RSS
   │
   ▼
Nyaa Provider
   │
   ▼
Ephemeral Release
   │
   ▼
Generic Title Parser
   │
   ├─ release group
   ├─ series title
   ├─ episode number
   └─ common technical metadata
   │
   ▼
Release Group Profile
   │
   ├─ parser profile/version
   └─ search profile/version
   │
   ▼
Parsed Release
   │
   ▼
Anime Matcher
   │
   ├─ matched
   ├─ ambiguous
   └─ unmatched
   │
   ▼
Review / Accept
   │
   ▼
Episode Ingestion
   │
   ├─ create
   ├─ idempotent update
   └─ replacement candidate
   │
   ▼
Existing Episode → DownloadJob flow
```

## Release is ephemeral

Raw Nyaa RSS results must not become a general-purpose release cache.

The existing `Release` object is a transient transport representation. Search results may be normalized, parsed, merged, and deduplicated in memory, but the raw result set is not persisted merely because it was discovered.

Persistent data should describe:

- Anime and its structured alternate titles
- Episode
- release-group definitions
- versioned parser/search profiles
- optional operational parser-health aggregates introduced later

A persisted Episode retains the external provenance needed by the existing download flow, such as source, source ID, source title, source URL, torrent URL, and info hash.

Anime keeps `title` as the representative display title and stores alternate forms in PostgreSQL JSONB `titles`, for example `{ "romaji": "Sousou no Frieren", "jp": "葬送のフリーレン", "ko": "장송의 프리렌", "en": "Frieren: Beyond Journey's End" }`. The release-discovery UI uses `titles.romaji` as its initial Nyaa search title and falls back to `title` when romaji is unavailable.

## Parsing strategy

Parsing is layered rather than group-only.

### 1. Generic parser

The generic parser handles common anime-release conventions without requiring a configured release group.

It should normalize title text for comparison/parsing purposes without mutating the original release title. Typical preprocessing includes:

- Unicode normalization
- whitespace normalization
- extension removal
- separator normalization for matching
- identification of common technical tokens

Generic extraction should prefer high-confidence episode forms:

1. `SxxEyy`
2. explicit episode-delimited numeric tokens
3. anime-style standalone episode numbers
4. ambiguous numeric tokens only as candidates, never as an automatic final decision

Batch, multi-episode, movie, NCOP/NCED, and other non-single-episode forms should not be forced into a normal Episode in this phase.

### 2. Release-group-specific parser profile

A known release group may have naming conventions that are more precise than the generic parser.

A group profile can refine or override generic extraction for fields such as:

- series title
- episode number
- episode title
- release group
- season number
- resolution
- source
- video codec
- audio codec
- bit depth
- release/version markers

The profile is declarative data. Regex patterns may be stored in the database, but they are executed by a constrained parser engine rather than as arbitrary application code.

### 3. Ambiguity is a first-class result

The parser must be able to report:

- `parsed`
- `ambiguous`
- `unparsed`
- `unsupported`

Unknown formats must fail safely instead of guessing an episode number or title.

## Versioned release profiles

Release groups and their parsing/search knowledge are persistent configuration.

Conceptual model:

```
ReleaseGroup
  ├─ ParserProfile v1
  ├─ ParserProfile v2
  └─ ParserProfile v3 (active)

  ├─ SearchProfile v1
  └─ SearchProfile v2 (active)
```

Profiles are immutable after activation. A changed convention creates a new version rather than modifying the active profile in place.

A profile should expose:

- group identity
- version
- status (`draft`, `active`, `retired`)
- ordered rules
- rule priority
- required/optional fields
- supported transformations
- creation and activation metadata

The parsed result should retain the profile identity/version used for interpretation whenever provenance is useful.

### Rule execution safety

Database-stored regex is allowed because the purpose is to let a user validate naming-convention changes without a code deployment.

However, regex execution must be constrained:

- validate syntax before activation
- restrict supported flags/transforms
- validate against representative samples
- enforce execution/resource limits in the parser engine
- do not evaluate generated Python or other executable code
- activate only a fully validated immutable profile

## Web-based parser validation

A release-group administrator should be able to create a draft profile and validate it against multiple samples.

The validation UI should support:

1. entering/editing a draft parser rule
2. testing several real release-title samples
3. displaying captured fields
4. showing failed required fields
5. comparing the draft against the currently active profile
6. activating the new version only after validation

For example:

```
Input
[Group] Anime - 28 [1080p][HEVC].mkv

Current v3
episode = null

Draft v4
episode = 28
resolution = 1080p
codec = HEVC
```

A multi-sample test is preferred over a single successful sample so that a rule is not accidentally tuned to one filename.

## Search strategy

Discovery should support multiple query templates instead of one hard-coded search string.

Conceptual query fields include:

- group
- title
- episode
- resolution
- codec
- other profile-defined tokens

A release-group search profile can define ordered query templates such as:

1. group + title + episode
2. title + episode
3. group + title
4. title
5. additional technical constraints when useful

The service may execute multiple queries and combine their results in memory.

Search specificity is progressive rather than absolute: a more specific query is attempted first, but missing optional naming tokens must not cause a valid release to disappear permanently.

Results from multiple queries must be deduplicated before parsing/matching, preferring stable source identity such as:

1. source + source ID
2. info hash
3. provider-specific fallback identity when neither is available

Search profile ordering and parsing profile ordering are separate concerns. Search field order is request intent and can be overridden by the discovery UI, while parsing rules remain independent.

## Anime matching

Matching is deterministic and conservative.

The matcher canonicalizes titles for comparison using operations such as:

- Unicode normalization
- case folding
- punctuation/separator normalization
- whitespace normalization

The result is one of:

- `matched`: exactly one valid Anime candidate
- `ambiguous`: multiple plausible Anime candidates
- `unmatched`: no candidate

Anime year/season may be used as supporting evidence or tie-breaking input, but release publication time must not be treated as authoritative Anime air year.

No automatic Anime creation is part of release ingestion in this phase.

## Episode ingestion

Ingestion is explicit: discovery and parsing never create an Episode by themselves.

An accepted release is passed to a transactional ingestion service.

### New Episode

If no Episode exists for the target Anime and episode number:

```
ParsedRelease
    ↓
EpisodeCreateData
    ↓
Episode
```

The Episode stores the provider provenance already supported by the current model.

### Same release: idempotent update

If the same external release is ingested again, the operation must be idempotent.

Stable identity should prefer:

- source + source ID
- source + info hash

A repeated ingestion updates mutable release metadata such as source title, source URL, torrent URL, size, seeders, leechers, downloads, and info hash as appropriate.

### Same episode, different release

If the Anime already has that episode number but the new release has a different source identity, ingestion must not silently replace the existing Episode.

The result is instead an explicit "existing episode / replacement candidate" state for later user review.

This protects DownloadJob, MediaAsset, playable media, and streaming artifacts already attached to the existing Episode.

### User-edited Episode data

Re-ingestion should not blindly overwrite user-maintained Episode fields.

In particular, a user-edited Episode title should remain unchanged unless the user explicitly accepts a replacement or title update.

Download and conversion status are execution state, not release metadata, and must never be reset by release discovery.

## Download boundary

Episode ingestion does not create or start a DownloadJob.

After an Episode exists, the existing explicit DownloadJob flow remains responsible for:

```
Episode
  → DownloadJob
  → Taskiq
  → qBittorrent
  → Media pipeline
```

This keeps discovery safe and allows a user to inspect candidates before any torrent activity begins.

## Future evolution

This design intentionally supports later automation without making it part of the current PR:

- periodic release discovery
- preferred release-group configuration per Anime
- automatic candidate ranking
- automatic Episode discovery
- automatic download scheduling

Those features must build on the same parsing, matching, and ingestion boundaries rather than bypassing them.
