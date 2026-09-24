import dashjs from "dashjs";
import type { MediaSource, VideoEngine } from "./types";

export class DashVideoEngine implements VideoEngine {
  private player: { reset: () => void } | null = null;
  private video: HTMLVideoElement | null = null;

  async attach(video: HTMLVideoElement, source: MediaSource): Promise<void> {
    this.detach();

    const player = dashjs.MediaPlayer().create();
    this.player = player;
    this.video = video;
    player.initialize(video, source.url, false);
  }

  detach(): void {
    if (this.player !== null) {
      this.player.reset();
      this.player = null;
    }

    if (this.video !== null) {
      this.video.pause();
      this.video.removeAttribute("src");
      this.video.load();
      this.video = null;
    }
  }
}
