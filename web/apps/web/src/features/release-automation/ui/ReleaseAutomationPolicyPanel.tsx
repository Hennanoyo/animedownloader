import { useEffect, useState } from "react";
import { Button, Checkbox, Input, Label } from "react-aria-components";
import {
  useReleaseAutomationPolicy,
  useReleaseAutomationPreview,
  useRunReleaseAutomation,
  useUpdateReleaseAutomationPolicy,
} from "../model/useReleaseAutomation";
import styles from "./ReleaseAutomationPolicyPanel.module.scss";

export default function ReleaseAutomationPolicyPanel({
  animeId,
}: {
  animeId: string;
}) {
  const policy = useReleaseAutomationPolicy(animeId);
  const preview = useReleaseAutomationPreview(animeId);
  const update = useUpdateReleaseAutomationPolicy(animeId);
  const run = useRunReleaseAutomation(animeId);

  const [enabled, setEnabled] = useState(false);
  const [minRankingScore, setMinRankingScore] = useState(0);
  const [requirePreferenceMatch, setRequirePreferenceMatch] = useState(true);

  useEffect(() => {
    if (!policy.data) return;
    setEnabled(policy.data.enabled);
    setMinRankingScore(policy.data.min_ranking_score);
    setRequirePreferenceMatch(policy.data.require_preference_match);
  }, [policy.data]);

  const hasChanges =
    policy.data !== undefined &&
    (enabled !== policy.data.enabled ||
      minRankingScore !== policy.data.min_ranking_score ||
      requirePreferenceMatch !== policy.data.require_preference_match);

  async function save() {
    await update.mutateAsync({
      enabled,
      min_ranking_score: minRankingScore,
      require_preference_match: requirePreferenceMatch,
    });
  }

  return (
    <section
      className={styles.panel}
      aria-labelledby="release-automation-heading"
    >
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Automatic downloads</p>
          <h2 id="release-automation-heading">
            Policy-controlled candidate selection
          </h2>
          <p className={styles.description}>
            Automation is opt-in. It only considers actionable, uniquely
            matched candidates and never replaces an existing Episode
            automatically.
          </p>
        </div>
        {update.isSuccess ? (
          <span className={styles.saved} role="status">
            Saved
          </span>
        ) : null}
      </div>

      <div className={styles.controls}>
        <Checkbox
          className={styles.checkbox}
          isSelected={enabled}
          onChange={setEnabled}
        >
          <span className={styles.checkboxBox} aria-hidden="true" />
          <span>
            <span className={styles.checkboxTitle}>
              Enable automatic candidate downloads
            </span>
            <span className={styles.checkboxDescription}>
              When enabled, eligible discovered candidates may create a
              DownloadJob automatically.
            </span>
          </span>
        </Checkbox>

        <div className={styles.field}>
          <Label htmlFor="release-automation-min-score">
            Minimum ranking score
          </Label>
          <Input
            id="release-automation-min-score"
            type="number"
            min={0}
            max={160}
            step={1}
            value={String(minRankingScore)}
            onChange={(event) => {
              const value = Number(event.target.value);
              setMinRankingScore(
                Number.isFinite(value) ? Math.max(0, Math.min(160, value)) : 0,
              );
            }}
          />
          <span className={styles.help}>0–160 from the existing ranking.</span>
        </div>

        <Checkbox
          className={styles.checkbox}
          isSelected={requirePreferenceMatch}
          isDisabled={!enabled}
          onChange={setRequirePreferenceMatch}
        >
          <span className={styles.checkboxBox} aria-hidden="true" />
          <span>
            <span className={styles.checkboxTitle}>
              Require all configured release preferences
            </span>
            <span className={styles.checkboxDescription}>
              A configured group, resolution, codec, or source must match
              before automation can select the candidate.
            </span>
          </span>
        </Checkbox>
      </div>

      {requirePreferenceMatch && enabled ? (
        <p className={styles.notice} role="note">
          At least one Anime release preference must be configured before a
          candidate can be selected automatically.
        </p>
      ) : null}

      {policy.isError ? (
        <p className={styles.error} role="alert">
          Failed to load automation policy: {policy.error.message}
        </p>
      ) : null}
      {update.isError ? (
        <p className={styles.error} role="alert">
          Failed to save automation policy: {update.error.message}
        </p>
      ) : null}
      {run.isError ? (
        <p className={styles.error} role="alert">
          Failed to queue automation run: {run.error.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          className={styles.secondaryButton}
          onPress={() => void run.mutateAsync()}
          isDisabled={!policy.data?.enabled || run.isPending}
        >
          {run.isPending ? "Queuing..." : "Run automation now"}
        </Button>
        <Button
          className={styles.primaryButton}
          onPress={() => void save()}
          isDisabled={policy.isPending || update.isPending || !hasChanges}
        >
          {update.isPending ? "Saving..." : "Save automation policy"}
        </Button>
      </div>

      <div className={styles.preview}>
        <div className={styles.previewHeader}>
          <div>
            <p className={styles.subkicker}>Dry-run preview</p>
            <h3>Current candidate decisions</h3>
          </div>
          {preview.isFetching ? (
            <span className={styles.meta}>Refreshing...</span>
          ) : null}
        </div>

        {preview.isError ? (
          <p className={styles.error} role="alert">
            Failed to load automation preview: {preview.error.message}
          </p>
        ) : preview.data?.length ? (
          <div className={styles.previewList}>
            {preview.data.slice(0, 6).map((item) => (
              <article className={styles.previewItem} key={item.candidate.id}>
                <div className={styles.previewMain}>
                  <strong>{item.candidate.source_title}</strong>
                  <span>
                    Episode {item.candidate.episode_number ?? "—"} · score{" "}
                    {item.candidate.ranking_score}
                  </span>
                </div>
                <span
                  className={item.eligible ? styles.eligible : styles.blocked}
                >
                  {item.eligible ? "Eligible" : "Blocked"}
                </span>
                <p>{item.reasons.join(" · ")}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className={styles.empty}>
            No current new or reviewed candidates are available for preview.
          </p>
        )}
      </div>
    </section>
  );
}
