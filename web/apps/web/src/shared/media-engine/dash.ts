import * as dashjs from "dashjs";
import type {
  MediaSource,
  VideoEngine,
  VideoEngineErrorHandler,
} from "./types";

interface DashPlayer {
  initialize(
    video: HTMLVideoElement,
    source: string,
    autoPlay: boolean,
  ): void;
  on(event: string, listener: (event: unknown) => void): void;
  off(event: string, listener: (event: unknown) => void): void;
  reset(): void;
}

export class DashVideoEngine implements VideoEngine {
  private player: DashPlayer | null = null;
  private video: HTMLVideoElement | null = null;
  private errorHandler: VideoEngineErrorHandler["onError"] | null = null;
  private handleError: ((event: unknown) => void) | null = null;

  async attach(
    video: HTMLVideoElement,
    source: MediaSource,
    handlers?: VideoEngineErrorHandler,
  ): Promise<void> {
    this.detach();

    const player = dashjs.MediaPlayer().create() as DashPlayer;
    this.player = player;
    this.video = video;
    this.errorHandler = handlers?.onError ?? null;

    const handleError = (event: unknown) => {
      this.errorHandler?.(
        new Error(extractDashErrorMessage(event)),
      );
    };
    this.handleError = handleError;

    player.on(dashjs.MediaPlayer.events.ERROR, handleError);
    player.initialize(video, source.url, false);
  }

  detach(): void {
    if (this.player !== null) {
      if (this.handleError !== null) {
        this.player.off(dashjs.MediaPlayer.events.ERROR, this.handleError);
        this.handleError = null;
      }
      this.player.reset();
      this.player = null;
    }

    this.errorHandler = null;

    if (this.video !== null) {
      this.video.pause();
      this.video.removeAttribute("src");
      this.video.load();
      this.video = null;
    }
  }
}

function extractDashErrorMessage(event: unknown): string {
  if (typeof event !== "object" || event === null) {
    return "dash.js reported an unrecoverable playback error.";
  }

  const errorEvent = event as {
    error?: {
      message?: unknown;
    };
    event?: {
      message?: unknown;
    };
    message?: unknown;
  };

  const candidates = [
    errorEvent.error?.message,
    errorEvent.event?.message,
    errorEvent.message,
  ];

  const message = candidates.find(
    (value): value is string => typeof value === "string" && value.length > 0,
  );

  return message
    ? `dash.js reported a playback error: ${message}.`
    : "dash.js reported an unrecoverable playback error.";
}
