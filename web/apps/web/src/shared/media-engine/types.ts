import type { PlaybackSource, PlaybackVideo } from "../../features/playback/model/types";

export type VideoSourceKind = "direct" | "hls" | "dash";

export interface SelectedVideoSource {
  kind: VideoSourceKind;
  source: PlaybackSource;
}

export interface VideoEngine {
  attach(video: HTMLVideoElement, source: PlaybackSource): Promise<void>;
  detach(): void;
}

export type VideoSourceSet = PlaybackVideo;
