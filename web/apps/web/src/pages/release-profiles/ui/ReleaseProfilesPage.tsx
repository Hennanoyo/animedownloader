import { useEffect, useState, type ReactNode } from "react";
import {
  Button,
  Checkbox,
  ComboBox,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  TextField,
  Tooltip,
  TooltipTrigger,
} from "react-aria-components";
import {
  parserFields,
  type ParserProfile,
  type ParserRule,
  type ReleaseGroupSummary,
  type ParserRuleInput,
} from "../../../entities/release/api/releaseProfiles";
import {
  useCreateReleaseGroup,
  useReleaseGroups,
} from "../../../entities/release/model/useReleaseGroups";
import {
  useActivateParserProfile,
  useCreateDraftFromObservation,
  useCreateParserDraft,
  useCreateParserSample,
  useDeleteParserSample,
  useParserComparison,
  useParserHealth,
  useParserProfiles,
  useParserSamples,
  useUpdateParserProfile,
  useValidateParserProfile,
} from "../../../features/release-profiles/model/useReleaseProfiles";
import styles from "./ReleaseProfilesPage.module.scss";

const FIELD_LABELS: Record<(typeof parserFields)[number], string> = {
  release_group: "Release group",
  series_title: "Series title",
  episode_number: "Episode number",
  episode_title: "Episode title",
  season_number: "Season number",
  resolution: "Resolution",
  source: "Source",
  video_codec: "Video codec",
  audio_codec: "Audio codec",
  bit_depth: "Bit depth",
};

const TRANSFORMS = [
  "identity",
  "strip",
  "normalize_spaces",
  "to_int",
  "lower",
  "upper",
] as const;

const TRANSFORM_LABELS: Record<(typeof TRANSFORMS)[number], string> = {
  identity: "Keep as matched",
  strip: "Trim whitespace",
  normalize_spaces: "Normalize spaces",
  to_int: "Convert to integer",
  lower: "Lowercase",
  upper: "Uppercase",
};

const TRANSFORM_DESCRIPTIONS: Record<(typeof TRANSFORMS)[number], string> = {
  identity: "Store the matched text unchanged.",
  strip: "Trim whitespace around the matched text.",
  normalize_spaces: "Collapse repeated whitespace and trim the result.",
  to_int: "Convert the matched value to an integer. Use this for episode, season, or bit depth.",
  lower: "Convert the matched text to lowercase.",
  upper: "Convert the matched text to uppercase.",
};

const RULE_GUIDANCE: Record<ParserRuleInput["field"], {
  placeholder: string;
  description: string;
  example: string;
}> = {
  release_group: {
    placeholder: "^\\[(?P<release_group>[^\\]]+)\\]",
    description: "Capture the release group, for example the name inside [ExampleSubs].",
    example: "[ExampleSubs] Frieren - 08 → ExampleSubs",
  },
  series_title: {
    placeholder: "(?P<series_title>.+?)(?=\\s+-?\\s+\\d{1,4})",
    description: "Capture the series title before the episode token.",
    example: "Frieren - 08 → Frieren",
  },
  episode_number: {
    placeholder: "(?P<episode_number>\\d{1,4})",
    description: "Capture the episode number. A numeric transform such as to_int is recommended.",
    example: "Episode 08 → 8",
  },
  episode_title: {
    placeholder: "(?P<episode_title>[^\\[]+)",
    description: "Capture the human-readable episode title while leaving technical brackets out.",
    example: "08 - Departure [1080p] → Departure",
  },
  season_number: {
    placeholder: "[Ss](?P<season_number>\\d{1,2})",
    description: "Capture the season number from S01-style notation.",
    example: "S02E03 → 2",
  },
  resolution: {
    placeholder: "(?P<resolution>2160p|1440p|1080p|720p|480p)",
    description: "Capture one supported resolution token.",
    example: "[1080p] → 1080p",
  },
  source: {
    placeholder: "(?P<source>WEB-DL|WEB|BluRay)",
    description: "Capture the release source token.",
    example: "[WEB-DL] → WEB-DL",
  },
  video_codec: {
    placeholder: "(?P<video_codec>HEVC|H\\.?265|x265)",
    description: "Capture the video codec token.",
    example: "[H.265] → H.265",
  },
  audio_codec: {
    placeholder: "(?P<audio_codec>AAC|FLAC|Opus)",
    description: "Capture the audio codec token.",
    example: "[AAC] → AAC",
  },
  bit_depth: {
    placeholder: "(?P<bit_depth>8|10|12)(?:-?bit)?",
    description: "Capture a bit depth such as 8, 10, or 12. Use to_int.",
    example: "[10bit] → 10",
  },
};

const EMPTY_RULE: ParserRuleInput = {
  field: "episode_number",
  pattern: "",
  priority: 10,
  required: true,
  flags: "",
  transform: "to_int",
};

function toEditableRules(profile: ParserProfile): ParserRuleInput[] {
  return profile.rules.map((rule) => ({
    field: rule.field,
    pattern: rule.pattern,
    priority: rule.priority,
    required: rule.required,
    flags: rule.flags,
    transform: rule.transform,
  }));
}

function Hint({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <TooltipTrigger delay={0}>
      <Button className={styles.hintButton} aria-label={label + " help"}>
        ?
      </Button>
      <Tooltip className={styles.hintTooltip}>{children}</Tooltip>
    </TooltipTrigger>
  );
}

export default function ReleaseProfilesPage() {
  const groups = useReleaseGroups();
  const [groupInput, setGroupInput] = useState("");
  const [newGroupName, setNewGroupName] = useState("");
  const [groupId, setGroupId] = useState("");
  const createGroup = useCreateReleaseGroup();
  const profiles = useParserProfiles(groupId);
  const samples = useParserSamples(groupId);
  const [selectedProfileId, setSelectedProfileId] = useState("");

  useEffect(() => {
    const nextGroup = groups.data?.find((group) => group.id === groupId);
    if (nextGroup) {
      setGroupInput(nextGroup.name);
      return;
    }
    if (!groupId && groups.data?.[0]) {
      setGroupId(groups.data[0].id);
      setGroupInput(groups.data[0].name);
    }
  }, [groupId, groups.data]);

  useEffect(() => {
    if (profiles.data?.length === 0) {
      setSelectedProfileId("");
      return;
    }
    if (!profiles.data?.some((profile) => profile.id === selectedProfileId)) {
      setSelectedProfileId(profiles.data?.[0]?.id ?? "");
    }
  }, [profiles.data, selectedProfileId]);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>Parser operations</p>
          <h1>Release profiles</h1>
          <p className={styles.description}>
            Maintain versioned release-group parser profiles, validate them against
            representative samples, and review observed parser drift before activating
            a new version.
          </p>
        </div>
      </header>

      <section className={styles.panel} aria-labelledby="group-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="group-heading">Release group</h2>
            <p>Groups are loaded from the database. Profile changes never modify the group itself.</p>
          </div>
        </div>

        <ComboBox
          className={styles.groupPicker}
          items={groups.data ?? []}
          inputValue={groupInput}
          selectedKey={groupId || null}
          onInputChange={setGroupInput}
          onSelectionChange={(key) => {
            if (key === null) return;
            const next = groups.data?.find((group) => group.id === key);
            if (!next) return;
            setGroupId(next.id);
            setGroupInput(next.name);
            setSelectedProfileId("");
          }}
          aria-label="Release group"
        >
          <Label className={styles.srOnly}>Release group</Label>
          <div className={styles.comboControl}>
            <Input placeholder={groups.isPending ? "Loading groups..." : "Select a release group"} />
            <Button aria-label="Show release groups">▾</Button>
          </div>
          <Popover className={styles.popover}>
            <ListBox className={styles.listBox}>
              {(group: ReleaseGroupSummary) => (
                <ListBoxItem
                  id={group.id}
                  textValue={group.name}
                  className={styles.listItem}
                >
                  <span>{group.name}</span>
                  <span className={styles.itemMeta}>{group.slug}</span>
                </ListBoxItem>
              )}
            </ListBox>
          </Popover>
        </ComboBox>

        <div className={styles.groupComposer}>
          <TextField
            className={styles.newGroupField}
            aria-label="New release group name"
          >
            <Label className={styles.srOnly}>New release group name</Label>
            <Input
              value={newGroupName}
              onChange={(event) => setNewGroupName(event.target.value)}
              placeholder="Add release group"
            />
          </TextField>
          <Button
            className={styles.secondaryButton}
            onPress={() => {
              void (async () => {
                const group = await createGroup.mutateAsync({
                  name: newGroupName.trim(),
                });
                setNewGroupName("");
                setGroupId(group.id);
                setGroupInput(group.name);
                setSelectedProfileId("");
              })();
            }}
            isDisabled={
              createGroup.isPending || newGroupName.trim().length === 0
            }
          >
            {createGroup.isPending ? "Adding..." : "Add group"}
          </Button>
        </div>

        {createGroup.isError ? (
          <p className={styles.error} role="alert">
            Failed to add release group: {createGroup.error.message}
          </p>
        ) : null}

        {groups.isError ? (
          <p className={styles.error} role="alert">
            Failed to load release groups: {groups.error.message}
          </p>
        ) : null}
      </section>

      {!groupId ? (
        <section className={styles.state}>
          <p>Select a release group to manage its parser profiles.</p>
        </section>
      ) : (
        <ReleaseProfileWorkspace
          key={groupId}
          groupId={groupId}
          profiles={profiles.data ?? []}
          profilesPending={profiles.isPending}
          profilesError={profiles.isError ? profiles.error.message : null}
          samples={samples.data ?? []}
          samplesPending={samples.isPending}
          selectedProfileId={selectedProfileId}
          onSelectProfile={setSelectedProfileId}
        />
      )}
    </main>
  );
}

interface WorkspaceProps {
  groupId: string;
  profiles: ParserProfile[];
  profilesPending: boolean;
  profilesError: string | null;
  samples: import("../../../entities/release/api/releaseProfiles").ParserSample[];
  samplesPending: boolean;
  selectedProfileId: string;
  onSelectProfile: (id: string) => void;
}

function ReleaseProfileWorkspace({
  groupId,
  profiles,
  profilesPending,
  profilesError,
  samples,
  samplesPending,
  selectedProfileId,
  onSelectProfile,
}: WorkspaceProps) {
  const selectedProfile =
    profiles.find((profile) => profile.id === selectedProfileId) ?? null;
  const createDraft = useCreateParserDraft();
  const createDraftFromObservation = useCreateDraftFromObservation();

  async function handleCreateDraft() {
    const profile = await createDraft.mutateAsync({ groupId });
    onSelectProfile(profile.id);
  }

  async function handleCreateDraftFromObservation(observationId: string) {
    const profile = await createDraftFromObservation.mutateAsync({ observationId });
    onSelectProfile(profile.id);
  }

  return (
    <div className={styles.workspace}>
      <section className={styles.panel} aria-labelledby="history-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="history-heading">Version history</h2>
            <p>Active profiles are immutable. Editing always happens in a draft version.</p>
          </div>
          <Button
            className={styles.primaryButton}
            onPress={() => void handleCreateDraft()}
            isDisabled={createDraft.isPending}
          >
            {createDraft.isPending ? "Creating..." : "New draft"}
          </Button>
        </div>

        {profilesPending ? <p className={styles.stateInline}>Loading profiles...</p> : null}
        {profilesError ? (
          <p className={styles.error} role="alert">Failed to load profiles: {profilesError}</p>
        ) : null}

        <div className={styles.profileList}>
          {profiles.map((profile) => (
            <Button
              key={profile.id}
              className={styles.profileCard}
              data-selected={profile.id === selectedProfileId}
              onPress={() => onSelectProfile(profile.id)}
            >
              <span className={styles.profileVersion}>v{profile.version}</span>
              <span className={styles.profileDetails}>
                <strong>{profile.status}</strong>
                <span>{profile.rules.length} rules</span>
              </span>
              {profile.activated_at ? (
                <span className={styles.profileDate}>
                  {profile.activated_at.toLocaleDateString()}
                </span>
              ) : null}
            </Button>
          ))}
          {!profilesPending && profiles.length === 0 ? (
            <div className={styles.emptyBox}>
              <strong>No parser profiles yet</strong>
              <span>Create a draft to start building the first version.</span>
            </div>
          ) : null}
        </div>
      </section>

      {selectedProfile ? (
        <ProfileEditor
          key={selectedProfile.id}
          profile={selectedProfile}
          onDraftFromObservation={handleCreateDraftFromObservation}
        />
      ) : null}

      <section className={styles.panel} aria-labelledby="samples-heading">
        <SampleManager
          groupId={groupId}
          samples={samples}
          samplesPending={samplesPending}
        />
      </section>
    </div>
  );
}

interface ProfileEditorProps {
  profile: ParserProfile;
  onDraftFromObservation: (observationId: string) => Promise<void>;
}

function ProfileEditor({
  profile,
  onDraftFromObservation,
}: ProfileEditorProps) {
  const [rules, setRules] = useState<ParserRuleInput[]>(() => toEditableRules(profile));
  const update = useUpdateParserProfile();
  const validate = useValidateParserProfile();
  const activate = useActivateParserProfile();
  const comparison = useParserComparison(profile.id);
  const health = useParserHealth(profile.id);

  useEffect(() => {
    validate.reset();
  }, [profile.id, validate.reset]);

  const canEdit = profile.status === "draft";
  const validationPassed = validate.data?.valid === true;

  function updateRule(index: number, patch: Partial<ParserRuleInput>) {
    setRules((current) =>
      current.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...patch } : rule,
      ),
    );
    validate.reset();
  }

  function addRule() {
    setRules((current) => [
      ...current,
      { ...EMPTY_RULE, priority: (current.length + 1) * 10 },
    ]);
    validate.reset();
  }

  function removeRule(index: number) {
    setRules((current) => current.filter((_, ruleIndex) => ruleIndex !== index));
    validate.reset();
  }

  async function saveRules() {
    await update.mutateAsync({ profileId: profile.id, rules });
    validate.reset();
  }

  return (
    <>
      <section className={styles.panel} aria-labelledby="rules-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="rules-heading">v{profile.version} · {profile.status}</h2>
            <p>
              {canEdit
                ? "Edit deterministic rules, then validate them against the representative sample set."
                : "This profile version is immutable. Create a new draft to make changes."}
            </p>
          </div>
          <div className={styles.actionRow}>
            {canEdit ? (
              <>
                <Button
                  className={styles.secondaryButton}
                  onPress={() => void saveRules()}
                  isDisabled={update.isPending}
                >
                  {update.isPending ? "Saving..." : "Save rules"}
                </Button>
                <Button
                  className={styles.secondaryButton}
                  onPress={() => void validate.mutateAsync({ profileId: profile.id })}
                  isDisabled={validate.isPending}
                >
                  {validate.isPending ? "Validating..." : "Validate samples"}
                </Button>
              </>
            ) : null}
            {canEdit ? (
              <Button
                className={styles.primaryButton}
                onPress={() => void activate.mutateAsync({ profileId: profile.id })}
                isDisabled={!validationPassed || activate.isPending}
              >
                {activate.isPending ? "Activating..." : "Activate version"}
              </Button>
            ) : null}
          </div>
        </div>

        {canEdit ? (
          <div className={styles.rules}>
            {rules.map((rule, index) => (
              <RuleRow
                key={index}
                rule={rule}
                index={index}
                onChange={(patch) => updateRule(index, patch)}
                onRemove={() => removeRule(index)}
              />
            ))}
            <Button className={styles.ghostButton} onPress={addRule}>
              + Add rule
            </Button>
          </div>
        ) : (
          <div className={styles.rules}>
            {profile.rules.map((rule) => (
              <ReadOnlyRule key={rule.id} rule={rule} />
            ))}
          </div>
        )}

        {update.isError ? <p className={styles.error} role="alert">{update.error.message}</p> : null}
        {validate.isError ? <p className={styles.error} role="alert">{validate.error.message}</p> : null}
        {activate.isError ? <p className={styles.error} role="alert">{activate.error.message}</p> : null}
        {validationPassed ? (
          <p className={styles.success} role="status">
            Validation passed across {validate.data?.sample_count ?? 0} samples. Activation is available.
          </p>
        ) : null}
        {validate.data && !validate.data.valid ? (
          <div className={styles.validationErrors}>
            {validate.data.errors.map((error) => <p key={error}>{error}</p>)}
          </div>
        ) : null}

        {validate.data ? (
          <div className={styles.sampleResults}>
            {validate.data.results.map((result) => (
              <article className={styles.sampleResult} key={result.sample_id}>
                <div>
                  <strong>{result.title}</strong>
                  <span>{result.parsed?.status ?? "error"}</span>
                </div>
                {result.error ? <p>{result.error}</p> : null}
                {result.parsed ? (
                  <p>
                    {result.parsed.series_title ?? "—"} · Episode {result.parsed.episode_number ?? "—"} ·{" "}
                    {result.parsed.resolution ?? "—"} · {result.parsed.video_codec ?? "—"}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className={styles.panel} aria-labelledby="compare-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="compare-heading">Active vs draft</h2>
            <p>Compare parser output over the representative samples before activation.</p>
          </div>
        </div>
        {comparison.isPending ? <p className={styles.stateInline}>Comparing...</p> : null}
        {comparison.isError ? <p className={styles.error} role="alert">{comparison.error.message}</p> : null}
        {comparison.isSuccess && comparison.data.active_version === null ? (
          <p className={styles.stateInline}>No active version exists for this group yet.</p>
        ) : null}
        {comparison.isSuccess && comparison.data.active_version !== null && comparison.data.differences.length === 0 ? (
          <p className={styles.success}>No sample output differences detected.</p>
        ) : null}
        {comparison.isSuccess && comparison.data.differences.length > 0 ? (
          <div className={styles.diffList}>
            {comparison.data.differences.map((difference) => (
              <article className={styles.diffCard} key={difference.sample_id}>
                <strong>{difference.title}</strong>
                {Object.entries(difference.fields).map(([field, values]) => (
                  <div className={styles.diffRow} key={field}>
                    <span>{field}</span>
                    <code>{String(values[0] ?? "—")}</code>
                    <span>→</span>
                    <code>{String(values[1] ?? "—")}</code>
                  </div>
                ))}
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className={styles.panel} aria-labelledby="health-heading">
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="health-heading">Parser health</h2>
            <p>Health is an observation signal; it never changes profile state automatically.</p>
          </div>
          {health.data?.drift_signal ? (
            <span className={styles.driftBadge}>Drift signal</span>
          ) : null}
        </div>

        {health.isPending ? <p className={styles.stateInline}>Loading health...</p> : null}
        {health.isError ? <p className={styles.error} role="alert">{health.error.message}</p> : null}
        {health.data ? (
          <>
            <div className={styles.healthGrid}>
              <HealthMetric label="Observed" value={String(health.data.total_count)} />
              <HealthMetric label="Parsed" value={String(health.data.parsed_count)} />
              <HealthMetric label="Ambiguous" value={String(health.data.ambiguous_count)} />
              <HealthMetric label="Unparsed" value={String(health.data.unparsed_count)} />
              <HealthMetric label="Unsupported" value={String(health.data.unsupported_count)} />
              <HealthMetric
                label="Failure rate"
                value={Math.round(health.data.failure_rate * 100) + "%"}
              />
            </div>
            {health.data.drift_reason ? (
              <p className={styles.driftReason}>{health.data.drift_reason}</p>
            ) : null}
            {health.data.recent_failures.length > 0 ? (
              <div className={styles.failureList}>
                {health.data.recent_failures.map((failure) => (
                  <article className={styles.failureItem} key={failure.id}>
                    <div>
                      <strong>{failure.title}</strong>
                      <span>{failure.status} · {failure.observed_at.toLocaleString()}</span>
                    </div>
                    <div className={styles.failureActions}>
                      {failure.failed_required_fields.length > 0 ? (
                        <span>Missing: {failure.failed_required_fields.join(", ")}</span>
                      ) : null}
                      <Button
                        className={styles.secondaryButton}
                        onPress={() => void onDraftFromObservation(failure.id)}
                      >
                        Create draft from failure
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className={styles.stateInline}>No recent parser failures were observed.</p>
            )}
          </>
        ) : null}
      </section>
    </>
  );
}

function RuleRow({
  rule,
  index,
  onChange,
  onRemove,
}: {
  rule: ParserRuleInput;
  index: number;
  onChange: (patch: Partial<ParserRuleInput>) => void;
  onRemove: () => void;
}) {
  const guidance = RULE_GUIDANCE[rule.field];

  return (
    <div className={styles.ruleRow}>
      <div className={styles.ruleMain}>
        <div className={styles.ruleNumber}>#{index + 1}</div>

        <div className={styles.ruleControl}>
          <div className={styles.labelRow}>
            <span className={styles.controlLabel}>Target field</span>
            <Hint label={"Rule " + (index + 1) + " target field"}>
              {guidance.description}
            </Hint>
          </div>
          <Select
            selectedKey={rule.field}
            onSelectionChange={(key) => {
              if (key !== null) {
                onChange({ field: String(key) as ParserRuleInput["field"] });
              }
            }}
            aria-label={"Rule " + (index + 1) + " target field"}
          >
            <Button className={styles.selectButton}>
              <span>{FIELD_LABELS[rule.field]}</span>
              <span aria-hidden="true">▾</span>
            </Button>
            <Popover className={styles.popover}>
              <ListBox className={styles.listBox}>
                {parserFields.map((field) => (
                  <ListBoxItem key={field} id={field} className={styles.listItem}>
                    {FIELD_LABELS[field]}
                  </ListBoxItem>
                ))}
              </ListBox>
            </Popover>
          </Select>
        </div>

        <div className={styles.rulePattern}>
          <div className={styles.labelRow}>
            <span className={styles.controlLabel}>Regex pattern</span>
            <Hint label={"Rule " + (index + 1) + " regex pattern"}>
              <strong>How regex matching works</strong>
              <p>
                The rule searches the normalized release title. Prefer a named
                capture matching the target field, such as{" "}
                <code>(?P&lt;episode_number&gt;\d{"{1,4}"})</code>. If no named
                capture exists, one capture group is used; otherwise the full
                match becomes the value.
              </p>
              <p>
                Example: <code>{guidance.example}</code>
              </p>
              <p>
                The pattern is checked before activation and against every
                representative sample during validation.
              </p>
            </Hint>
          </div>
          <Input
            aria-label={"Rule " + (index + 1) + " pattern"}
            value={rule.pattern}
            onChange={(event) => onChange({ pattern: event.target.value })}
            placeholder={guidance.placeholder}
          />
        </div>

        <Button
          className={styles.dangerButton}
          onPress={onRemove}
          aria-label={"Remove rule " + (index + 1)}
        >
          Remove
        </Button>
      </div>

      <div className={styles.ruleOptions}>
        <div className={styles.ruleControlCompact}>
          <div className={styles.labelRow}>
            <span className={styles.controlLabel}>Priority</span>
            <Hint label={"Rule " + (index + 1) + " priority"}>
              Lower numbers run first. Use the priority to control the order
              in which parser rules are evaluated.
            </Hint>
          </div>
          <Input
            type="number"
            min={0}
            aria-label={"Rule " + (index + 1) + " priority"}
            value={String(rule.priority)}
            onChange={(event) =>
              onChange({ priority: Number(event.target.value) || 0 })
            }
          />
        </div>

        <Checkbox
          className={styles.requiredCheckbox}
          isSelected={rule.required}
          onChange={(selected) => onChange({ required: selected })}
          aria-label={"Rule " + (index + 1) + " required"}
        >
          <span className={styles.checkboxMark} aria-hidden="true" />
          <span className={styles.requiredLabel}>
            <strong>Required</strong>
            <Hint label={"Rule " + (index + 1) + " required"}>
              If this rule does not match, validation treats the sample as
              missing a required field and the profile cannot be activated.
            </Hint>
          </span>
        </Checkbox>

        <div className={styles.ruleControlCompact}>
          <span className={styles.controlLabel}>Regex flags</span>
          <Input
            aria-label={"Rule " + (index + 1) + " regex flags"}
            value={rule.flags}
            onChange={(event) => onChange({ flags: event.target.value })}
            placeholder="i"
          />
        </div>

        <div className={styles.ruleControlCompact}>
          <div className={styles.labelRow}>
            <span className={styles.controlLabel}>Transform</span>
            <Hint label={"Rule " + (index + 1) + " transform"}>
              {TRANSFORM_DESCRIPTIONS[rule.transform]}
            </Hint>
          </div>
          <Select
            selectedKey={rule.transform}
            onSelectionChange={(key) => {
              if (key !== null) {
                onChange({
                  transform: String(key) as ParserRuleInput["transform"],
                });
              }
            }}
            aria-label={"Rule " + (index + 1) + " transform"}
          >
            <Button className={styles.selectButton}>
              <span>{TRANSFORM_LABELS[rule.transform]}</span>
              <span aria-hidden="true">▾</span>
            </Button>
            <Popover className={styles.popover}>
              <ListBox className={styles.listBox}>
                {TRANSFORMS.map((transform) => (
                  <ListBoxItem
                    key={transform}
                    id={transform}
                    className={styles.listItem}
                    textValue={TRANSFORM_LABELS[transform]}
                  >
                    <span>{TRANSFORM_LABELS[transform]}</span>
                  </ListBoxItem>
                ))}
              </ListBox>
            </Popover>
          </Select>
        </div>
      </div>
    </div>
  );
}

function ReadOnlyRule({ rule }: { rule: ParserRule }) {
  return (
    <div className={styles.readOnlyRule}>
      <span className={styles.ruleNumber}>#{rule.priority}</span>
      <strong>{FIELD_LABELS[rule.field]}</strong>
      <code>{rule.pattern}</code>
      <span>{rule.required ? "Required" : "Optional"}</span>
      <span>{TRANSFORM_LABELS[rule.transform]}</span>
    </div>
  );
}

function SampleManager({
  groupId,
  samples,
  samplesPending,
}: {
  groupId: string;
  samples: import("../../../entities/release/api/releaseProfiles").ParserSample[];
  samplesPending: boolean;
}) {
  const [title, setTitle] = useState("");
  const create = useCreateParserSample();
  const remove = useDeleteParserSample();

  async function handleCreate() {
    const value = title.trim();
    if (!value) return;
    await create.mutateAsync({ groupId, title: value, source: "nyaa" });
    setTitle("");
  }

  return (
    <>
      <div className={styles.sectionHeader}>
        <div>
          <h2 id="samples-heading">Representative samples</h2>
          <p>Keep varied real-world release titles here. Raw RSS is not stored just for health tracking.</p>
        </div>
      </div>

      <div className={styles.sampleComposer}>
        <TextField className={styles.sampleInput} aria-label="Sample release title">
          <Label className={styles.srOnly}>Sample release title</Label>
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="[ExampleSubs] Frieren Episode-08 [1080p][HEVC]"
          />
        </TextField>
        <Button
          className={styles.secondaryButton}
          onPress={() => void handleCreate()}
          isDisabled={create.isPending || title.trim().length === 0}
        >
          {create.isPending ? "Adding..." : "Add sample"}
        </Button>
      </div>

      {create.isError ? <p className={styles.error} role="alert">{create.error.message}</p> : null}

      {samplesPending ? <p className={styles.stateInline}>Loading samples...</p> : null}
      <div className={styles.samples}>
        {samples.map((sample) => (
          <div className={styles.sampleItem} key={sample.id}>
            <div className={styles.sampleContent}>
              <strong>{sample.title}</strong>
              <span>{sample.source} · added {sample.created_at.toLocaleDateString()}</span>
            </div>
            <Button
              className={styles.iconDanger}
              aria-label={"Delete sample " + sample.title}
              onPress={() => void remove.mutateAsync({ sampleId: sample.id, groupId })}
              isDisabled={remove.isPending}
            >
              ×
            </Button>
          </div>
        ))}
        {!samplesPending && samples.length === 0 ? (
          <p className={styles.stateInline}>No samples stored yet. Add at least two before activation.</p>
        ) : null}
      </div>
      {remove.isError ? <p className={styles.error} role="alert">{remove.error.message}</p> : null}
    </>
  );
}

function HealthMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.healthMetric}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
