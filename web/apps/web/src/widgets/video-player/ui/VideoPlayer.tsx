import { useEffect, useRef, useState } from "react";
import { Button } from "react-aria-components";
import type { Playback } from "../../../features/playback/model/types";
import { selectVideoEngine } from "../../../shared/media-engine/select";
import { JassubSubtitleEngine } from "../../../shared/media-engine/subtitle";
import type { SelectedVideoSource } from "../../../shared/media-engine/types";
import VideoControls from "./VideoControls";
import styles from "./VideoPlayer.module.scss";

interface Props {
  playback: Playback;
}

export default function VideoPlayer({ playback }: Props) {
  const playerRef = useRef<HTMLElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [selectedSource, setSelectedSource] =
    useState<SelectedVideoSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedSubtitleId, setSelectedSubtitleId] = useState<string | null>(
    playback.subtitles.find((subtitle) => subtitle.is_default)?.id ??
      playback.subtitles[0]?.id ??
      null,
  );

  useEffect(() => {
    const nextId =
      playback.subtitles.find(
        (subtitle) => subtitle.id === selectedSubtitleId,
      )?.id ??
      playback.subtitles.find((subtitle) => subtitle.is_default)?.id ??
      playback.subtitles[0]?.id ??
      null;

    setSelectedSubtitleId(nextId);
  }, [playback.subtitles, selectedSubtitleId]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === playerRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener(
        "fullscreenchange",
        handleFullscreenChange,
      );
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || playback.video === null) {
      setSelectedSource(null);
      setIsLoading(false);
      setCurrentTime(0);
      setDuration(0);
      setIsPlaying(false);
      return;
    }

    const selected = selectVideoEngine(video, playback.video);
    if (selected === null) {
      setSelectedSource(null);
      setError("This browser cannot play any available video source.");
      setIsLoading(false);
      return;
    }

    const engine = selected.engine;
    const source = selected.source;
    let active = true;

    const syncMediaState = () => {
      if (!active) {
        return;
      }

      setCurrentTime(video.currentTime);
      setDuration(Number.isFinite(video.duration) ? video.duration : 0);
      setIsPlaying(!video.paused);
      setVolume(video.volume);
      setIsMuted(video.muted);
    };

    const handleLoadedMetadata = () => {
      if (!active) {
        return;
      }
      syncMediaState();
      setIsLoading(false);
    };

    const handleDurationChange = () => {
      if (!active) {
        return;
      }
      setDuration(Number.isFinite(video.duration) ? video.duration : 0);
    };

    const handleTimeUpdate = () => {
      if (active) {
        setCurrentTime(video.currentTime);
      }
    };

    const handlePlay = () => {
      if (active) {
        setIsPlaying(true);
      }
    };

    const handlePause = () => {
      if (active) {
        setIsPlaying(false);
      }
    };

    const handleVolumeChange = () => {
      if (!active) {
        return;
      }
      setVolume(video.volume);
      setIsMuted(video.muted);
    };

    const handleError = () => {
      if (active) {
        setIsLoading(false);
        setError("The selected video source could not be loaded.");
      }
    };

    syncMediaState();
    setSelectedSource(source);
    setError(null);
    setIsLoading(true);
    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("durationchange", handleDurationChange);
    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("volumechange", handleVolumeChange);
    video.addEventListener("error", handleError);

    void engine.attach(video, source.source).catch((attachError: unknown) => {
      if (!active) {
        return;
      }
      setIsLoading(false);
      setError(
        attachError instanceof Error
          ? attachError.message
          : "The selected video source could not be loaded.",
      );
    });

    return () => {
      active = false;
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("durationchange", handleDurationChange);
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("volumechange", handleVolumeChange);
      video.removeEventListener("error", handleError);
      engine.detach();
    };
  }, [playback.video]);

  useEffect(() => {
    const video = videoRef.current;
    const subtitle = playback.subtitles.find(
      (item) => item.id === selectedSubtitleId,
    );
    if (!video || !subtitle) {
      return;
    }

    const engine = new JassubSubtitleEngine();
    let active = true;

    void engine
      .attach(video, subtitle, playback.fonts)
      .catch((subtitleError: unknown) => {
        if (!active) {
          return;
        }
        setError(
          subtitleError instanceof Error
            ? subtitleError.message
            : "The selected subtitle could not be loaded.",
        );
      });

    return () => {
      active = false;
      engine.detach();
    };
  }, [playback.fonts, playback.subtitles, selectedSubtitleId]);

  if (playback.video === null) {
    return (
      <section className={styles.player} aria-label="Video player">
        <p className={styles.message}>
          This episode does not have a current playable video yet.
        </p>
      </section>
    );
  }

  const togglePlayPause = () => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.paused) {
      void video.play().catch((playError: unknown) => {
        setError(
          playError instanceof Error
            ? playError.message
            : "Playback could not be started.",
        );
      });
    } else {
      video.pause();
    }
  };

  const seek = (nextTime: number) => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(nextTime)) {
      return;
    }

    video.currentTime = Math.max(0, Math.min(nextTime, duration));
    setCurrentTime(video.currentTime);
  };

  const changeVolume = (nextVolume: number) => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(nextVolume)) {
      return;
    }

    const clampedVolume = Math.max(0, Math.min(1, nextVolume));
    video.volume = clampedVolume;
    if (clampedVolume > 0 && video.muted) {
      video.muted = false;
    }
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (video) {
      video.muted = !video.muted;
    }
  };

  const toggleFullscreen = () => {
    const player = playerRef.current;
    if (!player) {
      return;
    }

    const run = async () => {
      if (document.fullscreenElement === player) {
        await document.exitFullscreen();
      } else {
        await player.requestFullscreen();
      }
      setError(null);
    };

    void run().catch((fullscreenError: unknown) => {
      setError(
        fullscreenError instanceof Error
          ? fullscreenError.message
          : "Fullscreen mode could not be activated.",
      );
    });
  };

  return (
    <section
      ref={playerRef}
      className={styles.player}
      aria-label="Video player"
    >
      <video
        ref={videoRef}
        crossOrigin="anonymous"
        className={styles.video}
        playsInline
        preload="metadata"
        data-testid="video-player"
      />

      <VideoControls
        video={videoRef.current}
        duration={duration}
        currentTime={currentTime}
        isPlaying={isPlaying}
        volume={volume}
        isMuted={isMuted}
        isFullscreen={isFullscreen}
        subtitles={playback.subtitles}
        selectedSubtitleId={selectedSubtitleId}
        thumbnails={playback.thumbnails}
        onPlayPause={togglePlayPause}
        onSeek={seek}
        onVolumeChange={changeVolume}
        onMuteToggle={toggleMute}
        onSubtitleChange={setSelectedSubtitleId}
        onFullscreenToggle={toggleFullscreen}
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
                seek(chapter.start_time_seconds);
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
