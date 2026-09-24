import Hls from "hls.js";
import type {
  MediaSource,
  VideoEngine,
  VideoEngineErrorHandler,
} from "./types";

export class HlsVideoEngine implements VideoEngine {
  private hls: Hls | null = null;
  private video: HTMLVideoElement | null = null;
  private errorHandler: VideoEngineErrorHandler["onError"] | null = null;
  private networkRecoveryAttempts = 0;
  private mediaRecoveryAttempts = 0;

  static isSupported(): boolean {
    return Hls.isSupported();
  }

  async attach(
    video: HTMLVideoElement,
    source: MediaSource,
    handlers?: VideoEngineErrorHandler,
  ): Promise<void> {
    this.detach();

    if (!Hls.isSupported()) {
      throw new Error("HLS.js is not supported by this browser.");
    }

    const hls = new Hls({
      autoStartLoad: true,
    });
    this.hls = hls;
    this.video = video;
    this.errorHandler = handlers?.onError ?? null;
    this.networkRecoveryAttempts = 0;
    this.mediaRecoveryAttempts = 0;

    const handleError = (
      _event: string,
      data: {
        fatal?: boolean;
        type?: string;
        details?: string;
      },
    ) => {
      if (!data.fatal) {
        return;
      }

      if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
        if (this.networkRecoveryAttempts === 0) {
          this.networkRecoveryAttempts += 1;
          hls.startLoad();
          return;
        }
      } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
        if (this.mediaRecoveryAttempts === 0) {
          this.mediaRecoveryAttempts += 1;
          hls.recoverMediaError();
          return;
        }
      }

      this.errorHandler?.(
        new Error(
          data.details
            ? `HLS.js reported a fatal error: ${data.details}.`
            : "HLS.js reported an unrecoverable playback error.",
        ),
      );
    };

    hls.on(Hls.Events.ERROR, handleError);

    hls.once(Hls.Events.MEDIA_ATTACHED, () => {
      hls.loadSource(source.url);
    });
    hls.attachMedia(video);
  }

  detach(): void {
    if (this.hls !== null) {
      this.hls.destroy();
      this.hls = null;
    }

    this.errorHandler = null;
    this.networkRecoveryAttempts = 0;
    this.mediaRecoveryAttempts = 0;

    if (this.video !== null) {
      this.video.pause();
      this.video.removeAttribute("src");
      this.video.load();
      this.video = null;
    }
  }
}
