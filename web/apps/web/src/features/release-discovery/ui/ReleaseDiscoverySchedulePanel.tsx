import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Button, Input, Label, ListBox, ListBoxItem, Popover, Select, SelectValue } from "react-aria-components";
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

const AUTOMATION_MODES = [
  { value: "off", label: "Collect candidates only", description: "Discovery stops after collecting and ranking releases." },
  { value: "accept", label: "Automatically assign Episodes", description: "Eligible candidates create Episodes without starting downloads." },
  { value: "download", label: "Assign Episodes and download", description: "Eligible candidates create Episodes and queue the existing DownloadJob flow." },
] as const;

const FIELD_LABELS: Record<string, string> = {
  group: "Group", title: "Title", episode: "Episode", resolution: "Resolution", codec: "Codec", source: "Source",
};

type AutomationMode = (typeof AUTOMATION_MODES)[number]["value"];

export default function ReleaseDiscoverySchedulePanel({ animeId }: { animeId: string }) {
  const schedule = useReleaseDiscoverySchedule(animeId);
  const generatedPlan = useReleaseDiscoverySearchPlan(animeId);
  const updateSchedule = useUpdateReleaseDiscoverySchedule(animeId);
  const runNow = useRunReleaseDiscoveryNow(animeId);

  const [enabled, setEnabled] = useState(false);
  const [intervalMinutes, setIntervalMinutes] = useState(360);
  const [automationMode, setAutomationMode] = useState<AutomationMode>("off");
  const [minRankingScore, setMinRankingScore] = useState(0);
  const [requirePlanMatch, setRequirePlanMatch] = useState(true);

  useEffect(() => {
    if (!schedule.data) return;
    setEnabled(schedule.data.enabled);
    setIntervalMinutes(schedule.data.interval_minutes);
    setAutomationMode(schedule.data.automation_mode);
    setMinRankingScore(schedule.data.automation_min_ranking_score);
    setRequirePlanMatch(schedule.data.automation_require_plan_match);
  }, [schedule.data]);

  const savedPlan = schedule.data?.search_plan ?? null;
  const generatedQuery = generatedPlan.data?.queries[0]?.query ?? null;
  const savedQuery = savedPlan ? buildSearchPlanQuery(savedPlan) : null;
  const hasChanges =
    schedule.data !== undefined &&
    (enabled !== schedule.data.enabled ||
      intervalMinutes !== schedule.data.interval_minutes ||
      automationMode !== schedule.data.automation_mode ||
      minRankingScore !== schedule.data.automation_min_ranking_score ||
      requirePlanMatch !== schedule.data.automation_require_plan_match);

  async function save() {
    await updateSchedule.mutateAsync({
      enabled,
      interval_minutes: intervalMinutes,
      automation_mode: automationMode,
      automation_min_ranking_score: minRankingScore,
      automation_require_plan_match: requirePlanMatch,
    });
  }

  const runLabel =
    automationMode === "download"
      ? "Discover & download now"
      : automationMode === "accept"
        ? "Discover & assign now"
        : "Discover now";

  return (
    <section className={styles.panel} aria-labelledby="release-discovery-schedule-heading">
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Discovery</p>
          <h2 id="release-discovery-schedule-heading">Schedule and automation</h2>
          <p className={styles.description}>
            The Search Plan saved in Find releases is the canonical input for scheduled discovery.
            Automation controls what happens after releases are parsed, matched, and ranked.
          </p>
        </div>
        {updateSchedule.isSuccess ? <span className={styles.saved} role="status">Saved</span> : null}
      </div>

      <section className={styles.plan} aria-label="Search Plan">
        <div className={styles.planBody}>
          <p className={styles.subkicker}>{savedPlan ? "Saved Search Plan" : "Default plan preview"}</p>
          <h3>{savedPlan ? savedPlan.title : "No saved Search Plan yet"}</h3>
          {savedQuery || generatedQuery ? <code className={styles.query}>{savedQuery ?? generatedQuery}</code> : null}
          {savedPlan ? (
            <p className={styles.planFields}>
              {savedPlan.field_order.filter((field) => savedPlan.enabled_fields.includes(field)).map((field) => FIELD_LABELS[field] ?? field).join(" → ")}
            </p>
          ) : (
            <p className={styles.meta}>Edit and save the Search Plan in Find releases before enabling periodic discovery.</p>
          )}
        </div>
      </section>

      <div className={styles.controls}>
        <label className={styles.toggle}>
          <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
          <span>Enable periodic discovery</span>
        </label>
        <Select
          className={styles.interval}
          selectedKey={String(intervalMinutes)}
          onSelectionChange={(key) => { if (key !== null) setIntervalMinutes(Number(key)); }}
          aria-label="Discovery interval"
        >
          <Label>Interval</Label>
          <Button className={styles.selectButton}><SelectValue /><span aria-hidden="true">▾</span></Button>
          <Popover className={styles.popover}><ListBox className={styles.listBox}>
            {INTERVALS.map((option) => <ListBoxItem key={option.value} id={String(option.value)} textValue={option.label} className={styles.option}>{option.label}</ListBoxItem>)}
          </ListBox></Popover>
        </Select>
      </div>

      <section className={styles.automation} aria-label="Discovery automation">
        <p className={styles.subkicker}>After discovery</p>
        <h3>Automation mode</h3>
        <Select
          className={styles.interval}
          selectedKey={automationMode}
          onSelectionChange={(key) => { if (key !== null) setAutomationMode(String(key) as AutomationMode); }}
          aria-label="Discovery automation mode"
        >
          <Label>What should happen to eligible candidates?</Label>
          <Button className={styles.selectButton}><SelectValue /><span aria-hidden="true">▾</span></Button>
          <Popover className={styles.popover}><ListBox className={styles.listBox}>
            {AUTOMATION_MODES.map((option) => <ListBoxItem key={option.value} id={option.value} textValue={option.label} className={styles.option}><strong>{option.label}</strong><span className={styles.optionDescription}>{option.description}</span></ListBoxItem>)}
          </ListBox></Popover>
        </Select>
        <div className={styles.selectionGrid}>
          <div className={styles.field}>
            <Label htmlFor="discovery-min-ranking-score">Minimum ranking score</Label>
            <Input id="discovery-min-ranking-score" type="number" min={0} max={160} step={1} value={String(minRankingScore)} onChange={(event) => { const value = Number(event.target.value); setMinRankingScore(Number.isFinite(value) ? Math.max(0, Math.min(160, value)) : 0); }} />
            <span className={styles.help}>Uses the ranking score produced from the saved Search Plan criteria.</span>
          </div>
          <label className={styles.toggle}>
            <input type="checkbox" checked={requirePlanMatch} disabled={automationMode === "off"} onChange={(event) => setRequirePlanMatch(event.target.checked)} />
            <span><strong>Require all configured Search Plan criteria</strong><small>Block automation when a configured group, resolution, codec, or source cannot be confirmed.</small></span>
          </label>
        </div>
      </section>

      {schedule.data?.next_run_at ? <p className={styles.meta}>Next run: {formatDate(schedule.data.next_run_at)}{schedule.data.last_run_at ? " · Last run: " + formatDate(schedule.data.last_run_at) : ""}</p> : null}
      {schedule.data?.last_run_status === "failed" ? <p className={styles.warning} role="alert">The previous discovery run failed. Open Discovery activity for query diagnostics.</p> : null}
      {schedule.isError ? <p className={styles.error} role="alert">Failed to load Discovery settings: {schedule.error.message}</p> : null}
      {updateSchedule.isError ? <p className={styles.error} role="alert">Failed to save Discovery settings: {updateSchedule.error.message}</p> : null}
      {runNow.isError ? <p className={styles.error} role="alert">Failed to start discovery: {runNow.error.message}</p> : null}

      <div className={styles.activityRow}><Link className={styles.activityLink} to="/release-inbox">Discovery activity</Link></div>
      <div className={styles.actions}>
        <Button className={styles.secondaryButton} onPress={() => void runNow.mutateAsync()} isDisabled={schedule.isPending || generatedPlan.isPending || runNow.isPending || savedPlan === null}>
          {runNow.isPending ? "Queuing..." : runLabel}
        </Button>
        <Button className={styles.primaryButton} onPress={() => void save()} isDisabled={!hasChanges || updateSchedule.isPending}>
          {updateSchedule.isPending ? "Saving..." : "Save discovery settings"}
        </Button>
      </div>
    </section>
  );
}

function buildSearchPlanQuery(plan: NonNullable<ReturnType<typeof useReleaseDiscoverySchedule>["data"]>["search_plan"]): string {
  if (!plan) return "";
  const values: Record<string, string | number | null> = { group: plan.group, title: plan.title, episode: plan.episode, resolution: plan.resolution, codec: plan.codec, source: plan.source };
  return plan.field_order.filter((field) => plan.enabled_fields.includes(field)).map((field) => values[field]).filter((value): value is string | number => value !== null && value !== "").join(" ");
}

function formatDate(value: Date): string {
  return value.toLocaleString();
}