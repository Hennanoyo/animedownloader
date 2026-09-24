export interface MediaSource {
  url: string;
  mime_type: string;
}

export type VideoSourceKind = "direct" | "hls" | "dash";

export interface SelectedVideoSource {
  kind: VideoSourceKind;
  source: MediaSource;
}

export interface VideoSourceSet {
  direct: MediaSource | null;
  hls: MediaSource | null;
  dash: MediaSource | null;
}

export interface VideoEngineErrorHandler {
  onError(error: Error): void;
}

export interface VideoEngine {
  attach(
    video: HTMLVideoElement,
    source: MediaSource,
    handlers?: VideoEngineErrorHandler,
  ): Promise<void>;
  detach(): void;
}
