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

## Release profile operations

Parser profiles have an explicit maintenance workflow after real-world release titles have accumulated.

For each release group:

1. keep the active parser profile immutable
2. create a new draft version when a convention changes or an observed failure needs review
3. maintain a representative sample set containing varied release-title shapes
4. validate the draft against the full sample set
5. compare draft output with the currently active profile
6. activate only after explicit user review and successful validation

Operational health is aggregate state attached to the parser profile. It counts observations by parse status and stores only non-parsed observation titles needed for manual investigation. Raw Nyaa/RSS payloads are not retained merely to calculate health.

A drift signal is deliberately heuristic. It highlights sustained failure rates or a cluster of recent failures for manual review; it never edits rules, creates or activates a profile automatically, or starts a download.

A failure observation can seed a draft and add its release title to the representative sample set. The resulting draft still follows the same validation and explicit-activation workflow.

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

Discovery builds one explicit query per user action.

Conceptual query fields include:

- group
- title
- episode
- resolution
- codec
- other profile-defined tokens

A Search Profile provides an ordered default field recipe. The discovery UI may enable/disable fields, edit their values, and override the field order for the current search.

The service executes exactly one provider query for each discovery action. A zero-result or provider failure is returned to the caller without automatic progressive broadening or retry.

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

## Periodic discovery and candidate inbox

Periodic discovery adds a persistence boundary after parsing, matching, and ranking without turning the normalized candidate into an Episode:

```
Schedule
   │
   ▼
Discovery Run (PostgreSQL)
   │
   ▼
Nyaa RSS / provider search
   │
   ▼
Ephemeral Release
   │
   ▼
Parse → Match → Rank
   │
   ▼
Normalized Candidate (PostgreSQL)
   │
   ▼
Candidate Inbox
   │
   ├─ review
   ├─ reject
   └─ stale
        │
        └─ later explicit acceptance workflow
```

A ReleaseDiscoverySchedule stores whether periodic collection is enabled, the minimum interval, and the next due time for one Anime. The scheduler claims due schedules inside a database transaction using row-level locking, advances the next due time, creates a queued ReleaseDiscoveryRun, and hands only the run ID to Taskiq. This keeps the API responsive and makes worker execution restartable.

A ReleaseDiscoveryRun records execution state and lightweight diagnostics such as the rendered search query, parser/search-profile version, candidate count, warning count, and timestamps. It is separate from DownloadJob and does not imply Episode state.

A ReleaseDiscoveryCandidate stores only the normalized data needed to inspect and later accept a release: provider/source identity, latest release metadata, parsed technical fields, Anime match evidence, and the ranking score/reasons. Raw Nyaa RSS/XML payloads are intentionally not persisted.

Candidate identity is scoped to (Anime, provider source, source ID). Repeated discovery therefore refreshes the existing candidate's latest observation instead of creating a duplicate candidate row. Provider fields such as seeders may change between observations; the candidate keeps the latest observed values and last_seen_at.

Candidate status is an explicit review state:

- new: discovered but not reviewed
- reviewed: inspected and retained
- rejected: intentionally excluded from later acceptance
- stale: intentionally retained for historical context but no longer considered current

Acceptance is intentionally absent from this phase. A future acceptance workflow must pass the existing deterministic Anime matching and Episode ingestion/replacement guards rather than directly creating or mutating Episodes from the candidate row.

The candidate inbox is not a general-purpose release cache. API list endpoints use bounded limits, and any destructive cleanup must be an explicit action rather than a side effect of discovery.

## Anime release preferences and ranking

An Anime may store optional release preferences for:

- release group
- resolution
- video codec
- source

These preferences are advisory discovery metadata. They are not part of Episode ingestion and do not trigger downloads.

When the target Anime is supplied to discovery, candidates receive a deterministic preference score:

| Preference | Score |
| --- | ---: |
| release group | 100 |
| resolution | 30 |
| video codec | 20 |
| source | 10 |

Only configured fields contribute to the score. A candidate that does not match the target Anime is not promoted by preference scoring. When a preference exists, discovery sorts by preference score first, then actionable parse status, current seeders, and release title for deterministic tie-breaking.

The API returns the score and explicit match reasons so the UI can explain ordering. Seeders are not treated as a preference and cannot outweigh an explicit preference match.

## Future evolution

This design intentionally keeps later automation behind explicit workflow boundaries:

- explicit candidate acceptance and Episode ingestion
- policy-controlled automatic candidate selection
- automatic download scheduling
- additional release providers

Periodic discovery and candidate ranking are now implemented as a review-only collection layer. Future automation must consume the normalized candidate contract rather than bypassing parsing, matching, provenance, and replacement safeguards.

Those features must build on the same parsing, matching, and ingestion boundaries rather than bypassing them.
