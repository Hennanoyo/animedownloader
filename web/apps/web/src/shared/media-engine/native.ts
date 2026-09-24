import type {
  SelectedVideoSource,
  VideoEngine,
  VideoSourceSet,
} from "./types";

export function selectNativeSource(
  video: HTMLVideoElement,
  sources: VideoSourceSet,
): SelectedVideoSource | null {
  if (sources.hls && video.canPlayType(sources.hls.mime_type)) {
    return { kind: "hls", source: sources.hls };
  }

  if (sources.direct) {
    return { kind: "direct", source: sources.direct };
  }

  return null;
}

export class NativeVideoEngine implements VideoEngine {
  private video: HTMLVideoElement | null = null;

  async attach(
    video: HTMLVideoElement,
    source: SelectedVideoSource["source"],
  ): Promise<void> {
    this.detach();
    this.video = video;
    video.src = source.url;
    video.load();
  }

  detach(): void {
    if (this.video === null) {
      return;
    }

    this.video.pause();
    this.video.removeAttribute("src");
    this.video.load();
    this.video = null;
  }
}
