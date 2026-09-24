import Hls from "hls.js";
import type { MediaSource, VideoEngine } from "./types";

export class HlsVideoEngine implements VideoEngine {
  private hls: Hls | null = null;
  private video: HTMLVideoElement | null = null;

  static isSupported(): boolean {
    return Hls.isSupported();
  }

  async attach(video: HTMLVideoElement, source: MediaSource): Promise<void> {
    this.detach();

    if (!Hls.isSupported()) {
      throw new Error("HLS.js is not supported by this browser.");
    }

    const hls = new Hls();
    this.hls = hls;
    this.video = video;
    hls.loadSource(source.url);
    hls.attachMedia(video);
  }

  detach(): void {
    if (this.hls !== null) {
      this.hls.destroy();
      this.hls = null;
    }

    if (this.video !== null) {
      this.video.pause();
      this.video.removeAttribute("src");
      this.video.load();
      this.video = null;
    }
  }
}
