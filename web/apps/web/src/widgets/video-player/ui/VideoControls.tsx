import { useEffect, useRef, useState } from "react";
import {
  Button,
  Label,
  Slider,
  SliderThumb,
  SliderTrack,
} from "react-aria-components";
import type { ThumbnailCue } from "../../../shared/media-engine/thumbnail";
import { findThumbnailCue, parseThumbnailVtt } from "../../../shared/media-engine/thumbnail";
import type { Playback } from "../../../features/playback/model/types";
import styles from "./VideoPlayer.module.scss";

interface Props {
  video: HTMLVideoElement | null;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  volume: number;
  isMuted: boolean;
  isFullscreen: boolean;
  subtitles: Playback["subtitles"];
  selectedSubtitleId: string | null;
  thumbnails: Playback["thumbnails"];
  controlsVisible: boolean;
  onPlayPause: () => void;
  onSeek: (seconds: number) => void;
  onVolumeChange: (value: number) => void;
  onMuteToggle: () => void;
  onSubtitleChange: (id: string | null) => void;
  onFullscreenToggle: () => void;
  onControlsEnter: () => void;
  onControlsLeave: () => void;
}

type ControlIconName =
  | "play"
  | "pause"
  | "volume"
  | "volume-muted"
  | "fullscreen-enter"
  | "fullscreen-exit"
  | "captions";

export default function VideoControls({
  video,
  duration,
  currentTime,
  isPlaying,
  volume,
  isMuted,
  isFullscreen,
  subtitles,
  selectedSubtitleId,
  thumbnails,
  controlsVisible,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onSubtitleChange,
  onFullscreenToggle,
  onControlsEnter,
  onControlsLeave,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [thumbnailCues, setThumbnailCues] = useState<ThumbnailCue[]>([]);
  const [previewTime, setPreviewTime] = useState<number | null>(null);
  const [previewPercent, setPreviewPercent] = useState(0);
  const [scrubTime, setScrubTime] = useState<number | null>(null);

  useEffect(() => {
    setThumbnailCues([]);
    if (!thumbnails) {
      return;
    }

    const controller = new AbortController();

    void fetch(thumbnails.vtt_url, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Thumbnail metadata request failed with HTTP ${response.status}.`,
          );
        }
        return response.text();
      })
      .then((content) => {
        setThumbnailCues(parseThumbnailVtt(content));
      })
      .catch((thumbnailError: unknown) => {
        if (
          thumbnailError instanceof DOMException &&
          thumbnailError.name === "AbortError"
        ) {
          return;
        }
        console.warn("Unable to load thumbnail metadata.", thumbnailError);
      });

    return () => {
      controller.abort();
    };
  }, [thumbnails]);

  const previewCue =
    previewTime === null
      ? null
      : findThumbnailCue(thumbnailCues, previewTime);
  const displayedTime = scrubTime ?? currentTime;

  const updatePreview = (clientX: number) => {
    const track = trackRef.current;
    if (!track || duration <= 0) {
      return;
    }

    const bounds = track.getBoundingClientRect();
    if (bounds.width <= 0) {
      return;
    }

    const percent = Math.min(
      1,
      Math.max(0, (clientX - bounds.left) / bounds.width),
    );
    const nextTime = percent * duration;
    setPreviewTime(nextTime);
    setPreviewPercent(percent * 100);
  };

  return (
    <div
      className={`${styles.controls} ${controlsVisible ? "" : styles.controlsHidden}`}
      aria-label="Video controls"
      onPointerEnter={() => {
        onControlsEnter();
      }}
      onPointerLeave={() => {
        onControlsLeave();
      }}
    >
      <div className={styles.timeline}>
        {previewCue ? (
          <div
            className={styles.thumbnailPreview}
            style={{
              left: `${Math.min(92, Math.max(8, previewPercent))}%`,
              backgroundImage: `url("${thumbnails?.sprite_url ?? previewCue.url}")`,
              backgroundPosition: `-${previewCue.x}px -${previewCue.y}px`,
            }}
            role="img"
            aria-label={`Preview at ${formatTime(previewTime ?? 0)}`}
          >
            <span>{formatTime(previewTime ?? 0)}</span>
          </div>
        ) : null}

        <Slider
          aria-label="Seek"
          value={Math.min(displayedTime, duration)}
          minValue={0}
          maxValue={Math.max(duration, 1)}
          step={0.1}
          isDisabled={!video || duration <= 0}
          onChange={(value) => {
            setScrubTime(Number(value));
          }}
          onChangeEnd={(value) => {
            const nextTime = Number(value);
            setScrubTime(null);
            onSeek(nextTime);
          }}
        >
          <SliderTrack
            ref={trackRef}
            className={styles.timelineTrack}
            data-testid="timeline-track"
            onPointerMove={(event) => {
              updatePreview(event.clientX);
            }}
            onPointerLeave={() => {
              setPreviewTime(null);
            }}
          >
            <span
              className={styles.timelineProgress}
              style={{
                width: `${duration > 0 ? Math.min(100, (displayedTime / duration) * 100) : 0}%`,
              }}
            />
            <SliderThumb className={styles.timelineThumb} />
          </SliderTrack>
        </Slider>
      </div>

      <div className={styles.controlRow}>
        <Button
          className={`${styles.controlButton} ${styles.iconButton} ${styles.playButton}`}
          aria-label={isPlaying ? "Pause" : "Play"}
          title={isPlaying ? "Pause" : "Play"}
          onPress={onPlayPause}
          isDisabled={!video}
        >
          <ControlIcon name={isPlaying ? "pause" : "play"} />
        </Button>

        <span className={styles.timeDisplay} aria-live="off">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        <div className={styles.volumeControls}>
          <Button
            className={`${styles.controlButton} ${styles.iconButton}`}
            aria-label={
              isMuted || volume === 0 ? "Unmute" : "Mute"
            }
            title={isMuted || volume === 0 ? "Unmute" : "Mute"}
            aria-pressed={isMuted || volume === 0}
            onPress={onMuteToggle}
            isDisabled={!video}
          >
            <ControlIcon
              name={isMuted || volume === 0 ? "volume-muted" : "volume"}
            />
          </Button>
          <Slider
            aria-label="Volume"
            value={isMuted ? 0 : volume}
            minValue={0}
            maxValue={1}
            step={0.01}
            isDisabled={!video}
            onChange={(value) => onVolumeChange(Number(value))}
          >
            <SliderTrack className={styles.volumeTrack}>
              <span
                className={styles.volumeProgress}
                style={{
                  width: `${(isMuted ? 0 : volume) * 100}%`,
                }}
              />
              <SliderThumb className={styles.volumeThumb} />
            </SliderTrack>
          </Slider>
        </div>

        {subtitles.length > 0 ? (
          <Label className={styles.subtitleControl}>
            <span className={styles.subtitleLabel}>
              <ControlIcon name="captions" />
              <span>Subtitles</span>
            </span>
            <select
              value={selectedSubtitleId ?? ""}
              onChange={(event) =>
                onSubtitleChange(event.target.value || null)
              }
            >
              <option value="">Off</option>
              {subtitles.map((subtitle) => (
                <option key={subtitle.id} value={subtitle.id}>
                  {subtitle.title ?? subtitle.language ?? "Subtitle"}
                  {subtitle.is_forced ? " (forced)" : ""}
                </option>
              ))}
            </select>
          </Label>
        ) : null}

        <Button
          className={`${styles.controlButton} ${styles.iconButton}`}
          aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          onPress={onFullscreenToggle}
        >
          <ControlIcon
            name={isFullscreen ? "fullscreen-exit" : "fullscreen-enter"}
          />
        </Button>
      </div>
    </div>
  );
}

function ControlIcon({ name }: { name: ControlIconName }) {
  const sharedProps = {
    className: styles.controlIcon,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "play":
      return (
        <svg {...sharedProps} fill="currentColor" stroke="none">
          <path d="M8 5.14v13.72L19 12 8 5.14Z" />
        </svg>
      );
    case "pause":
      return (
        <svg {...sharedProps}>
          <path d="M7 5v14M17 5v14" />
        </svg>
      );
    case "volume":
      return (
        <svg {...sharedProps}>
          <path d="M4 9v6h4l5 4V5L8 9H4Z" />
          <path d="M16 9.5a4 4 0 0 1 0 5M18.5 7a7 7 0 0 1 0 10" />
        </svg>
      );
    case "volume-muted":
      return (
        <svg {...sharedProps}>
          <path d="M4 9v6h4l5 4V5L8 9H4Z" />
          <path d="m17 9 4 6M21 9l-4 6" />
        </svg>
      );
    case "fullscreen-enter":
      return (
        <svg {...sharedProps}>
          <path d="M8 3H3v5M16 3h5v5M8 21H3v-5M21 16v5h-5" />
        </svg>
      );
    case "fullscreen-exit":
      return (
        <svg {...sharedProps}>
          <path d="M9 3v6H3M15 3v6h6M9 21v-6H3M21 15h-6v6" />
        </svg>
      );
    case "captions":
      return (
        <svg {...sharedProps}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M7 10h4M7 14h5M14 10h3M14 14h3" />
        </svg>
      );
  }
}

function formatTime(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "00:00";
  }

  const totalSeconds = Math.floor(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return (
      String(hours).padStart(2, "0") +
      ":" +
      String(minutes).padStart(2, "0") +
      ":" +
      String(seconds).padStart(2, "0")
    );
  }

  return (
    String(minutes).padStart(2, "0") +
    ":" +
    String(seconds).padStart(2, "0")
  );
}
