import { useEffect, useState } from "react";
import { Button, Label, Select, SelectValue, Popover, ListBox, ListBoxItem } from "react-aria-components";
import {
  useReleaseDiscoverySchedule,
  useReleaseDiscoverySearchPlan,
  useRunReleaseDiscoveryNow,
  useUpdateReleaseDiscoverySchedule,
} from "../model/useReleaseDiscoveryCandidates";
import styles from "./ReleaseDiscoverySchedulePanel.module.scss";

const INTERVALS = [
  { value: 60, label: "Every hour" },
  { value: 180, label: "Every 3 hours" },
  { value: 360, label: "Every 6 hours" },
  { value: 720, label: "Every 12 hours" },
  { value: 1440, label: "Every 24 hours" },
];

export default function ReleaseDiscoverySchedulePanel({
  animeId,
}: {
  animeId: string;
}) {
  const query = useReleaseDiscoverySchedule(animeId);
  const searchPlan = useReleaseDiscoverySearchPlan(animeId);
  const update = useUpdateReleaseDiscoverySchedule(animeId);
  const runNow = useRunReleaseDiscoveryNow(animeId);

  const [enabled, setEnabled] = useState(false);
  const [intervalMinutes, setIntervalMinutes] = useState(360);

  useEffect(() => {
    if (!query.data) return;
    setEnabled(query.data.enabled);
    setIntervalMinutes(query.data.interval_minutes);
  }, [query.data]);

  async function save() {
    await update.mutateAsync({
      enabled,
      interval_minutes: intervalMinutes,
    });
  }

  return (
    <section className={styles.panel} aria-labelledby="release-discovery-schedule-heading">
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Discovery schedule</p>
          <h2 id="release-discovery-schedule-heading">Keep a candidate inbox updated</h2>
          <p className={styles.description}>
            Scheduled runs only collect and rank release candidates. They never create
            Episodes or start downloads automatically.
          </p>
        </div>
        {update.isSuccess ? (
          <span className={styles.saved} role="status">
            Saved
          </span>
        ) : null}
      </div>

      <div className={styles.controls}>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          <span>Enable periodic discovery</span>
        </label>

        <Select
          className={styles.interval}
          selectedKey={String(intervalMinutes)}
          onSelectionChange={(key) => {
            if (key !== null) setIntervalMinutes(Number(key));
          }}
          aria-label="Discovery interval"
        >
          <Label>Interval</Label>
          <Button className={styles.selectButton}>
            <SelectValue />
            <span aria-hidden="true">▾</span>
          </Button>
          <Popover className={styles.popover}>
            <ListBox className={styles.listBox}>
              {INTERVALS.map((option) => (
                <ListBoxItem
                  key={option.value}
                  id={String(option.value)}
                  textValue={option.label}
                  className={styles.option}
                >
                  {option.label}
                </ListBoxItem>
              ))}
            </ListBox>
          </Popover>
        </Select>
      </div>

      {searchPlan.isPending ? (
        <p className={styles.meta}>Loading scheduled search plan...</p>
      ) : searchPlan.isError ? (
        <p className={styles.error} role="alert">
          Failed to load search plan: {searchPlan.error.message}
        </p>
      ) : searchPlan.data ? (
        <details className={styles.plan}>
          <summary>
            Search plan · {searchPlan.data.queries.length}{" "}
            {searchPlan.data.queries.length === 1 ? "query" : "queries"}
            {searchPlan.data.search_profile_version
              ? " · Search profile v" + searchPlan.data.search_profile_version
              : " · default profile"}
          </summary>
          <div className={styles.planBody}>
            <p>
              This is the same bounded plan used by <strong>Discover now</strong>{" "}
              and periodic discovery. Previewing it does not contact Nyaa.
            </p>
            <ol className={styles.planList}>
              {searchPlan.data.queries.map((item) => (
                <li key={item.position} className={styles.planItem}>
                  <code>{item.query}</code>
                  <span>{item.fields.join(" · ")}</span>
                </li>
              ))}
            </ol>
          </div>
        </details>
      ) : null}

      {query.data?.next_run_at ? (
        <p className={styles.meta}>
          Next run: {formatDate(query.data.next_run_at)}
          {query.data.last_run_at
            ? " · Last run: " + formatDate(query.data.last_run_at)
            : ""}
        </p>
      ) : null}

      {query.data?.last_run_status === "failed" ? (
        <p className={styles.warning} role="alert">
          The previous scheduled discovery run failed. Check the discovery inbox for run details.
        </p>
      ) : null}

      {query.isError ? (
        <p className={styles.error} role="alert">
          Failed to load discovery schedule: {query.error.message}
        </p>
      ) : null}
      {update.isError ? (
        <p className={styles.error} role="alert">
          Failed to save discovery schedule: {update.error.message}
        </p>
      ) : null}
      {runNow.isError ? (
        <p className={styles.error} role="alert">
          Failed to start discovery: {runNow.error.message}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          className={styles.secondaryButton}
          onPress={() => void runNow.mutateAsync()}
          isDisabled={query.isPending || runNow.isPending}
        >
          {runNow.isPending ? "Queuing..." : "Discover now"}
        </Button>
        <Button
          className={styles.primaryButton}
          onPress={() => void save()}
          isDisabled={
            query.isPending ||
            update.isPending ||
            !query.data ||
            (enabled === query.data.enabled &&
              intervalMinutes === query.data.interval_minutes)
          }
        >
          {update.isPending ? "Saving..." : "Save schedule"}
        </Button>
      </div>
    </section>
  );
}

function formatDate(value: Date): string {
  return value.toLocaleString();
}
