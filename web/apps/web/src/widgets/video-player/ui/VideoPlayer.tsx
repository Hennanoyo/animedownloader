import { useEffect, useRef, useState } from "react";
import { Button } from "react-aria-components";
import type { Playback } from "../../../features/playback/model/types";
import {
  NativeVideoEngine,
  selectNativeSource,
} from "../../../shared/media-engine/native";
import type { SelectedVideoSource } from "../../../shared/media-engine/types";
import styles from "./VideoPlayer.module.scss";

interface Props {
  playback: Playback;
}

export default function VideoPlayer({ playback }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [selectedSource, setSelectedSource] =
    useState<SelectedVideoSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || playback.video === null) {
      setSelectedSource(null);
      setIsLoading(false);
      return;
    }

    const source = selectNativeSource(video, playback.video);
    if (source === null) {
      setSelectedSource(null);
      setError("This browser cannot play any available video source.");
      setIsLoading(false);
      return;
    }

    const engine = new NativeVideoEngine();
    let active = true;

    const handleLoadedMetadata = () => {
      if (active) {
        setIsLoading(false);
      }
    };
    const handleError = () => {
      if (active) {
        setIsLoading(false);
        setError("The selected video source could not be loaded.");
      }
    };

    setSelectedSource(source);
    setError(null);
    setIsLoading(true);
    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("error", handleError);
    void engine.attach(video, source.source);

    return () => {
      active = false;
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("error", handleError);
      engine.detach();
    };
  }, [playback.video]);

  if (playback.video === null) {
    return (
      <section className={styles.player} aria-label="Video player">
        <p className={styles.message}>
          This episode does not have a current playable video yet.
        </p>
      </section>
    );
  }

  return (
    <section className={styles.player} aria-label="Video player">
      <video
        ref={videoRef}
        className={styles.video}
        controls
        playsInline
        preload="metadata"
        data-testid="video-player"
      />
      <div className={styles.meta}>
        {isLoading ? <span>Loading media...</span> : null}
        {selectedSource ? (
          <span className={styles.source}>
            Source: {formatSourceKind(selectedSource.kind)}
          </span>
        ) : null}
        <span>
          {playback.subtitles.length} subtitle
          {playback.subtitles.length === 1 ? "" : "s"}
        </span>
      </div>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      {playback.chapters.length > 0 ? (
        <div className={styles.chapters}>
          <h2 className={styles.chaptersTitle}>Chapters</h2>
          {playback.chapters.map((chapter) => (
            <Button
              key={chapter.id}
              className={styles.chapter}
              onPress={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime = chapter.start_time_seconds;
                }
              }}
            >
              <span>{chapter.title ?? "Untitled chapter"}</span>
              <span className={styles.chapterTime}>
                {formatTime(chapter.start_time_seconds)}
              </span>
            </Button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function formatSourceKind(kind: SelectedVideoSource["kind"]): string {
  return kind.toUpperCase();
}

function formatTime(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value));
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
    String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0")
  );
}
