import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "react-aria-components";
import type { Playback } from "../../../features/playback/model/types";
import { selectVideoEngine } from "../../../shared/media-engine/select";
import { JassubSubtitleEngine } from "../../../shared/media-engine/subtitle";
import type {
  SelectedVideoSource,
  VideoSourceKind,
} from "../../../shared/media-engine/types";
import VideoControls from "./VideoControls";
import { useVideoPlayerKeyboard } from "./useVideoPlayerKeyboard";
import styles from "./VideoPlayer.module.scss";

interface Props {
  playback: Playback;
  onRetryMedia: () => Promise<Playback>;
}

export default function VideoPlayer({ playback, onRetryMedia }: Props) {
  const playerRef = useRef<HTMLElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [selectedSource, setSelectedSource] =
    useState<SelectedVideoSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [mediaRetryAttempt, setMediaRetryAttempt] = useState(0);
  const [isRetryingMedia, setIsRetryingMedia] = useState(false);
  const [sourceFailures, setSourceFailures] = useState<{
    video: Playback["video"];
    kinds: VideoSourceKind[];
  }>({
    video: playback.video,
    kinds: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);
  const controlsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
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

  const clearControlsTimer = useCallback(() => {
    if (controlsTimerRef.current !== null) {
      clearTimeout(controlsTimerRef.current);
      controlsTimerRef.current = null;
    }
  }, []);

  const showControls = useCallback(() => {
    setControlsVisible(true);
    clearControlsTimer();

    if (isPlaying) {
      controlsTimerRef.current = setTimeout(() => {
        setControlsVisible(false);
        controlsTimerRef.current = null;
      }, 2500);
    }
  }, [clearControlsTimer, isPlaying]);

  const keepControlsVisible = useCallback(() => {
    setControlsVisible(true);
    clearControlsTimer();
  }, [clearControlsTimer]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === playerRef.current);
      showControls();
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener(
        "fullscreenchange",
        handleFullscreenChange,
      );
      clearControlsTimer();
    };
  }, [clearControlsTimer, showControls]);

  useEffect(() => {
    showControls();
    return clearControlsTimer;
  }, [clearControlsTimer, showControls]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || playback.video === null) {
      setSelectedSource(null);
      setError(null);
      setMediaError(null);
      setIsLoading(false);
      setCurrentTime(0);
      setDuration(0);
      setIsPlaying(false);
      return;
    }

    const excludedSourceKinds =
      sourceFailures.video === playback.video ? sourceFailures.kinds : [];
    const selected = selectVideoEngine(
      video,
      playback.video,
      excludedSourceKinds,
    );
    if (selected === null) {
      setSelectedSource(null);
      const message =
        excludedSourceKinds.length > 0
          ? "All available video sources failed. Retry to try them again."
          : "This browser cannot play any available video source.";
      setMediaError(message);
      setError(message);
      setIsLoading(false);
      return;
    }

    const engine = selected.engine;
    const source = selected.source;
    let active = true;
    let failureHandled = false;

    const handleMediaFailure = (failure: Error | string) => {
      if (!active || failureHandled) {
        return;
      }
      failureHandled = true;
      const message = failure instanceof Error ? failure.message : failure;
      setIsLoading(false);
      setMediaError(message);
      setError(message);
      setSourceFailures((current) => {
        const currentKinds =
          current.video === playback.video ? current.kinds : [];
        if (currentKinds.includes(source.kind)) {
          return current;
        }
        return {
          video: playback.video,
          kinds: [...currentKinds, source.kind],
        };
      });
    };

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
      setMediaError(null);
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
      handleMediaFailure("The selected video source could not be loaded.");
    };

    syncMediaState();
    setSelectedSource(source);
    setError(null);
    setMediaError(null);
    setIsLoading(true);
    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("durationchange", handleDurationChange);
    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("volumechange", handleVolumeChange);
    video.addEventListener("error", handleError);

    void engine
      .attach(video, source.source, { onError: handleMediaFailure })
      .catch((attachError: unknown) => {
        if (!active) {
          return;
        }
        const message =
          attachError instanceof Error
            ? attachError.message
            : "The selected video source could not be loaded.";
        handleMediaFailure(message);
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
  }, [mediaRetryAttempt, playback.video, sourceFailures]);

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

  const togglePlayPause = useCallback(() => {
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
  }, []);

  const seek = useCallback(
    (nextTime: number) => {
      const video = videoRef.current;
      if (!video || !Number.isFinite(nextTime)) {
        return;
      }

      video.currentTime = Math.max(0, Math.min(nextTime, duration));
      setCurrentTime(video.currentTime);
    },
    [duration],
  );

  const changeVolume = useCallback((nextVolume: number) => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(nextVolume)) {
      return;
    }

    const clampedVolume = Math.max(0, Math.min(1, nextVolume));
    video.volume = clampedVolume;
    if (clampedVolume > 0 && video.muted) {
      video.muted = false;
    }
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (video.muted) {
      video.muted = false;
      return;
    }

    if (video.volume === 0) {
      video.volume = 1;
      return;
    }

    video.muted = true;
  }, []);

  const toggleFullscreen = useCallback(() => {
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
  }, []);

  useVideoPlayerKeyboard({
    playerRef,
    currentTime,
    volume,
    onPlayPause: togglePlayPause,
    onSeek: seek,
    onVolumeChange: changeVolume,
    onMuteToggle: toggleMute,
    onFullscreenToggle: toggleFullscreen,
    onControlsShow: showControls,
  });

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
    <section
      ref={playerRef}
      className={styles.player}
      aria-label="Video player"
      tabIndex={0}
      aria-keyshortcuts="Space K ArrowLeft ArrowRight ArrowUp ArrowDown M F"
      onPointerMove={showControls}
      onFocus={showControls}
    >
      <div className={styles.mediaSurface}>
        <video
          ref={videoRef}
          crossOrigin="anonymous"
          className={styles.video}
          playsInline
          preload="metadata"
          data-testid="video-player"
          onClick={() => {
            playerRef.current?.focus({ preventScroll: true });
            togglePlayPause();
            showControls();
          }}
          onPointerMove={showControls}
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
          controlsVisible={controlsVisible}
          onPlayPause={togglePlayPause}
          onSeek={seek}
          onVolumeChange={changeVolume}
          onMuteToggle={toggleMute}
          onSubtitleChange={setSelectedSubtitleId}
          onFullscreenToggle={toggleFullscreen}
          onControlsEnter={keepControlsVisible}
          onControlsLeave={showControls}
        />
      </div>

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
        <div className={styles.error} role="alert">
          <p>{error}</p>
          {mediaError !== null ? (
            <Button
              className={styles.retryButton}
              isDisabled={isRetryingMedia}
              onPress={() => {
                setIsRetryingMedia(true);
                void onRetryMedia()
                  .then((nextPlayback) => {
                    if (nextPlayback.video === playback.video) {
                      setSourceFailures({
                        video: playback.video,
                        kinds: [],
                      });
                      setMediaRetryAttempt((attempt) => attempt + 1);
                    }
                  })
                  .catch((retryError: unknown) => {
                    setError(
                      retryError instanceof Error
                        ? `Unable to refresh playback: ${retryError.message}`
                        : "Unable to refresh playback.",
                    );
                  })
                  .finally(() => {
                    setIsRetryingMedia(false);
                  });
              }}
            >
              {isRetryingMedia ? "Refreshing media..." : "Retry media"}
            </Button>
          ) : null}
        </div>
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
