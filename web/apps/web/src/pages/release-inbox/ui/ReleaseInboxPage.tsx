import { useMemo, useState } from "react";
import {
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from "react-aria-components";
import { Link } from "@tanstack/react-router";
import { useAnimes } from "../../../features/anime-create/model/useCreateAnime";
import {
  type ReleaseCandidateStatus,
} from "../../../entities/release/api/discoveryCandidates";
import {
  useAcceptReleaseDiscoveryCandidate,
  useReleaseDiscoveryCandidates,
  useReleaseDiscoveryRuns,
  useUpdateReleaseDiscoveryCandidate,
} from "../../../features/release-discovery/model/useReleaseDiscoveryCandidates";
import type {
  ReleaseDiscoveryCandidate,
  ReleaseDiscoveryCandidateAcceptance,
} from "../../../entities/release/api/discoveryCandidates";
import styles from "./ReleaseInboxPage.module.scss";

const FILTERS: Array<{
  value: "all" | ReleaseCandidateStatus;
  label: string;
}> = [
  { value: "all", label: "All candidates" },
  { value: "new", label: "New" },
  { value: "reviewed", label: "Reviewed" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "stale", label: "Stale" },
];

export default function ReleaseInboxPage() {
  const animes = useAnimes();
  const [status, setStatus] = useState<"all" | ReleaseCandidateStatus>("all");
  const candidateQuery = useReleaseDiscoveryCandidates(
    status === "all" ? {} : { status },
  );
  const runs = useReleaseDiscoveryRuns();
  const update = useUpdateReleaseDiscoveryCandidate();

  const animeTitles = useMemo(
    () => new Map((animes.data ?? []).map((anime) => [anime.id, anime.title])),
    [animes.data],
  );

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Release discovery</p>
          <h1>Candidate inbox</h1>
          <p className={styles.description}>
            Review normalized release candidates collected by scheduled or
            manual discovery. Acceptance creates or updates an Episode, but
            never starts a download automatically.
          </p>
        </div>
        <Link className={styles.secondaryLink} to="/animes">
          Anime
        </Link>
      </header>

      <section className={styles.toolbar} aria-label="Candidate filters">
        <Select
          className={styles.filter}
          selectedKey={status}
          onSelectionChange={(key) => {
            if (key !== null) setStatus(String(key) as typeof status);
          }}
          aria-label="Candidate status"
        >
          <Label>Status</Label>
          <Button className={styles.selectButton}>
            <SelectValue />
            <span aria-hidden="true">▾</span>
          </Button>
          <Popover className={styles.popover}>
            <ListBox className={styles.listBox}>
              {FILTERS.map((filter) => (
                <ListBoxItem
                  key={filter.value}
                  id={filter.value}
                  textValue={filter.label}
                  className={styles.option}
                >
                  {filter.label}
                </ListBoxItem>
              ))}
            </ListBox>
          </Popover>
        </Select>

        <Link className={styles.secondaryLink} to="/release-profiles">
          Release profiles
        </Link>
      </section>

      {candidateQuery.isPending ? (
        <p className={styles.state}>Loading candidates...</p>
      ) : null}
      {candidateQuery.isError ? (
        <p className={styles.error} role="alert">
          Failed to load candidates: {candidateQuery.error.message}
        </p>
      ) : null}

      <section className={styles.runs} aria-labelledby="runs-heading">
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.kicker}>Run history</p>
            <h2 id="runs-heading">Recent discovery runs</h2>
          </div>
        </div>
        {runs.isPending ? (
          <p className={styles.stateInline}>Loading runs...</p>
        ) : runs.data?.length ? (
          <div className={styles.runList}>
            {runs.data.slice(0, 8).map((run) => (
              <article className={styles.runCard} key={run.id}>
                <div>
                  <strong>{animeTitles.get(run.anime_id) ?? "Unknown Anime"}</strong>
                  <span>{formatDate(run.created_at)}</span>
                </div>
                <div className={styles.runStats}>
                  <span data-status={run.status}>{run.status}</span>
                  <span>{run.candidate_count} candidates</span>
                  {run.warning_count > 0 ? (
                    <span>{run.warning_count} warnings</span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className={styles.stateInline}>No discovery runs yet.</p>
        )}
      </section>

      <section className={styles.candidates} aria-labelledby="candidates-heading">
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.kicker}>Inbox</p>
            <h2 id="candidates-heading">
              {candidateQuery.data?.length ?? 0} candidates
            </h2>
          </div>
        </div>

        {candidateQuery.data?.length === 0 ? (
          <p className={styles.state}>No candidates match this filter.</p>
        ) : (
          <div className={styles.list}>
            {candidateQuery.data?.map((candidate) => (
              <CandidateCard
                key={candidate.id}
                candidate={candidate}
                animeTitle={animeTitles.get(candidate.anime_id) ?? "Unknown Anime"}
                updateStatus={update}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

interface CandidateCardProps {
  candidate: ReleaseDiscoveryCandidate;
  animeTitle: string;
  updateStatus: ReturnType<typeof useUpdateReleaseDiscoveryCandidate>;
}

function CandidateCard({
  candidate,
  animeTitle,
  updateStatus,
}: CandidateCardProps) {
  const accept = useAcceptReleaseDiscoveryCandidate();
  const [replacementEpisode, setReplacementEpisode] =
    useState<ReleaseDiscoveryCandidateAcceptance["existing_episode"]>(null);

  const canAccept =
    (candidate.status === "new" || candidate.status === "reviewed") &&
    candidate.match_status === "matched" &&
    candidate.parse_status === "parsed" &&
    candidate.episode_number !== null;

  async function handleAccept(replaceEpisodeId?: string) {
    const result = await accept.mutateAsync({
      candidateId: candidate.id,
      replaceEpisodeId,
    });
    if (
      result.status === "replacement_candidate" &&
      result.existing_episode !== null
    ) {
      setReplacementEpisode(result.existing_episode);
      return;
    }
    setReplacementEpisode(null);
  }

  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <p className={styles.animeName}>{animeTitle}</p>
          <h3>{candidate.source_title}</h3>
          <p className={styles.meta}>
            {formatCandidateMeta(candidate)} · Last seen{" "}
            {formatDate(candidate.last_seen_at)}
          </p>
        </div>
        <div className={styles.badges}>
          <span className={styles.status} data-status={candidate.status}>
            {candidate.status}
          </span>
          {candidate.ranking_score > 0 ? (
            <span className={styles.rank}>
              Preferred {candidate.ranking_score}
            </span>
          ) : null}
        </div>
      </div>

      <div className={styles.details}>
        <span>
          <strong>Episode</strong>
          {candidate.episode_number ?? "—"}
        </span>
        <span>
          <strong>Group</strong>
          {candidate.release_group ?? "—"}
        </span>
        <span>
          <strong>Resolution</strong>
          {candidate.resolution ?? "—"}
        </span>
        <span>
          <strong>Source</strong>
          {candidate.source ?? "—"}
        </span>
        <span>
          <strong>Codec</strong>
          {candidate.video_codec ?? "—"}
        </span>
        <span>
          <strong>Match</strong>
          {candidate.match_status}
        </span>
        <span>
          <strong>Parse</strong>
          {candidate.parse_status}
        </span>
      </div>

      {candidate.ranking_reasons.length > 0 ? (
        <p className={styles.reasons}>{candidate.ranking_reasons.join(" · ")}</p>
      ) : null}

      {candidate.parse_warnings.length > 0 ? (
        <p className={styles.warning}>
          {candidate.parse_warnings.join(" · ")}
        </p>
      ) : null}

      {replacementEpisode !== null ? (
        <div className={styles.warning} role="alert">
          <strong>
            Episode {candidate.episode_number} already exists as "
            {replacementEpisode.title}".
          </strong>
          <span>
            This does not replace it automatically. Confirm replacement below;
            existing download or media history will still block replacement.
          </span>
          <div className={styles.actions}>
            <Button
              className={styles.primaryButton}
              onPress={() => void handleAccept(replacementEpisode.id)}
              isDisabled={accept.isPending}
            >
              {accept.isPending ? "Replacing..." : "Replace Episode"}
            </Button>
          </div>
        </div>
      ) : null}

      {accept.isError ? (
        <p className={styles.error} role="alert">
          Failed to accept candidate: {accept.error.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <a
          className={styles.secondaryLink}
          href={candidate.page_url}
          target="_blank"
          rel="noreferrer"
        >
          View release
        </a>
        <a
          className={styles.secondaryLink}
          href={candidate.torrent_url}
          target="_blank"
          rel="noreferrer"
        >
          Torrent
        </a>
        {canAccept ? (
          <Button
            className={styles.primaryButton}
            onPress={() => void handleAccept()}
            isDisabled={accept.isPending}
          >
            {accept.isPending ? "Accepting..." : "Accept"}
          </Button>
        ) : candidate.status === "accepted" ? (
          <span className={styles.stateInline}>Accepted</span>
        ) : null}
        {candidate.status === "new" ? (
          <Button
            className={styles.secondaryButton}
            onPress={() =>
              void updateStatus.mutateAsync({
                candidateId: candidate.id,
                status: "reviewed",
              })
            }
            isDisabled={updateStatus.isPending || accept.isPending}
          >
            Mark reviewed
          </Button>
        ) : null}
        {candidate.status !== "rejected" && candidate.status !== "accepted" ? (
          <Button
            className={styles.dangerButton}
            onPress={() =>
              void updateStatus.mutateAsync({
                candidateId: candidate.id,
                status: "rejected",
              })
            }
            isDisabled={updateStatus.isPending || accept.isPending}
          >
            Reject
          </Button>
        ) : null}
        <Link
          className={styles.detailLink}
          to="/animes/$animeId"
          params={{ animeId: candidate.anime_id }}
        >
          Open Anime
        </Link>
      </div>
    </article>
  );
}

function formatDate(value: Date): string {
  return value.toLocaleString();
}

function formatCandidateMeta(
  candidate: ReleaseDiscoveryCandidate,
): string {
  return [
    candidate.provider_source,
    candidate.size ?? "Unknown size",
    "Seeders " + (candidate.seeders ?? 0),
  ].join(" · ");
}
