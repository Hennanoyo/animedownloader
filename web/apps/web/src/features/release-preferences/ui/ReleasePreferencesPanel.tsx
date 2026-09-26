import { useEffect, useMemo, useState } from "react";
import {
  Button,
  ComboBox,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  TextField,
} from "react-aria-components";
import { useReleaseGroups } from "../../../entities/release/model/useReleaseGroups";
import {
  useAnimeReleasePreference,
  useUpdateAnimeReleasePreference,
} from "../model/useAnimeReleasePreference";
import styles from "./ReleasePreferencesPanel.module.scss";

const RESOLUTION_OPTIONS = ["2160p", "1080p", "720p", "480p"];
const VIDEO_CODEC_OPTIONS = ["HEVC", "AVC", "AV1", "VP9"];
const SOURCE_OPTIONS = ["WEB", "WEB-DL", "WEBRip", "Blu-ray", "HDTV"];

export default function ReleasePreferencesPanel({
  animeId,
}: {
  animeId: string;
}) {
  const query = useAnimeReleasePreference(animeId);
  const groups = useReleaseGroups();
  const mutation = useUpdateAnimeReleasePreference(animeId);

  const [releaseGroupId, setReleaseGroupId] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");
  const [videoCodec, setVideoCodec] = useState("");
  const [source, setSource] = useState("");

  useEffect(() => {
    if (query.data === undefined) return;
    setReleaseGroupId(query.data?.release_group_id ?? null);
    setResolution(query.data?.resolution ?? "");
    setVideoCodec(query.data?.video_codec ?? "");
    setSource(query.data?.source ?? "");
  }, [query.data]);

  const releaseGroupItems = useMemo(
    () => groups.data?.map((group) => group.name) ?? [],
    [groups.data],
  );

  const hasChanges =
    query.data === undefined
      ? false
      : releaseGroupId !== (query.data?.release_group_id ?? null) ||
        resolution !== (query.data?.resolution ?? "") ||
        videoCodec !== (query.data?.video_codec ?? "") ||
        source !== (query.data?.source ?? "");

  async function handleSave() {
    await mutation.mutateAsync({
      release_group_id: releaseGroupId,
      resolution: resolution.trim() || null,
      video_codec: videoCodec.trim() || null,
      source: source.trim() || null,
    });
  }

  return (
    <section
      className={styles.panel}
      aria-label="Release preferences"
    >
      <div className={styles.header}>
        <div>
          <p className={styles.kicker}>Release preferences</p>
          <h2 id="release-preferences-heading">Preferred release shape</h2>
          <p className={styles.description}>
            These preferences only order discovery results. They never start a
            download or replace an existing Episode automatically.
          </p>
        </div>
        {mutation.isSuccess ? (
          <span className={styles.saved} role="status">
            Saved
          </span>
        ) : null}
      </div>

      <div className={styles.grid}>
        <ComboBox
          className={styles.field}
          items={releaseGroupItems}
          selectedKey={
            groups.data?.find((group) => group.id === releaseGroupId)?.name ??
            null
          }
          onSelectionChange={(key) => {
            const name = key === null ? null : String(key);
            setReleaseGroupId(
              name === null
                ? null
                : (groups.data?.find((group) => group.name === name)?.id ??
                    null),
            );
          }}
        >
          <Label>Release group</Label>
          <div className={styles.control}>
            <Input aria-label="Release group" />
            <Button aria-label="Show release group options">▾</Button>
          </div>
          <Popover className={styles.popover}>
            <ListBox>
              {(item: string) => (
                <ListBoxItem
                  id={item}
                  textValue={item}
                  className={styles.option}
                >
                  {item}
                </ListBoxItem>
              )}
            </ListBox>
          </Popover>
        </ComboBox>

        <TextField className={styles.field}>
          <Label>Resolution</Label>
          <ComboBox
            items={RESOLUTION_OPTIONS}
            selectedKey={resolution || null}
            inputValue={resolution}
            allowsCustomValue
            onInputChange={setResolution}
            onSelectionChange={(key) =>
              setResolution(key === null ? "" : String(key))
            }
          >
            <div className={styles.control}>
              <Input aria-label="Resolution" />
              <Button aria-label="Show resolution options">▾</Button>
            </div>
            <Popover className={styles.popover}>
              <ListBox>
                {(item: string) => (
                  <ListBoxItem
                    id={item}
                    textValue={item}
                    className={styles.option}
                  >
                    {item}
                  </ListBoxItem>
                )}
              </ListBox>
            </Popover>
          </ComboBox>
        </TextField>

        <TextField className={styles.field}>
          <Label>Video codec</Label>
          <ComboBox
            items={VIDEO_CODEC_OPTIONS}
            selectedKey={videoCodec || null}
            inputValue={videoCodec}
            allowsCustomValue
            onInputChange={setVideoCodec}
            onSelectionChange={(key) =>
              setVideoCodec(key === null ? "" : String(key))
            }
          >
            <div className={styles.control}>
              <Input aria-label="Video codec" />
              <Button aria-label="Show video codec options">▾</Button>
            </div>
            <Popover className={styles.popover}>
              <ListBox>
                {(item: string) => (
                  <ListBoxItem
                    id={item}
                    textValue={item}
                    className={styles.option}
                  >
                    {item}
                  </ListBoxItem>
                )}
              </ListBox>
            </Popover>
          </ComboBox>
        </TextField>

        <TextField className={styles.field}>
          <Label>Source</Label>
          <ComboBox
            items={SOURCE_OPTIONS}
            selectedKey={source || null}
            inputValue={source}
            allowsCustomValue
            onInputChange={setSource}
            onSelectionChange={(key) =>
              setSource(key === null ? "" : String(key))
            }
          >
            <div className={styles.control}>
              <Input aria-label="Source" />
              <Button aria-label="Show source options">▾</Button>
            </div>
            <Popover className={styles.popover}>
              <ListBox>
                {(item) => (
                  <ListBoxItem
                    id={item}
                    textValue={item}
                    className={styles.option}
                  >
                    {item}
                  </ListBoxItem>
                )}
              </ListBox>
            </Popover>
          </ComboBox>
        </TextField>
      </div>

      {query.isError ? (
        <p className={styles.error} role="alert">
          Failed to load release preferences.
        </p>
      ) : null}
      {mutation.isError ? (
        <p className={styles.error} role="alert">
          Failed to save release preferences:{" "}
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Unknown error"}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          className={styles.saveButton}
          isDisabled={
            query.isPending || mutation.isPending || !hasChanges
          }
          onPress={() => void handleSave()}
        >
          {mutation.isPending ? "Saving..." : "Save preferences"}
        </Button>
      </div>
    </section>
  );
}
