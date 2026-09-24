import JASSUB from "jassub";
import modernWasmUrl from "jassub/dist/jassub-worker-modern.wasm?url";
import wasmUrl from "jassub/dist/jassub-worker.wasm?url";
import workerUrl from "jassub/dist/jassub-worker.js?url";
import type { PlaybackSubtitle } from "./subtitle-types";
import type { PlaybackFontSource } from "./subtitle-types";

export interface SubtitleEngine {
  attach(
    video: HTMLVideoElement,
    subtitle: PlaybackSubtitle,
    fonts: PlaybackFontSource[],
  ): Promise<void>;
  detach(): void;
}

export class JassubSubtitleEngine implements SubtitleEngine {
  private renderer: JASSUB | null = null;

  async attach(
    video: HTMLVideoElement,
    subtitle: PlaybackSubtitle,
    fonts: PlaybackFontSource[],
  ): Promise<void> {
    this.detach();

    if (subtitle.format?.toLowerCase() !== "ass") {
      throw new Error("Only ASS subtitles are supported by JASSUB.");
    }

    const renderer = new JASSUB({
      video,
      subUrl: subtitle.url,
      fonts: fonts.map((font) => font.url),
      workerUrl,
      wasmUrl,
      modernWasmUrl,
    });

    this.renderer = renderer;
    await renderer.ready;
  }

  detach(): void {
    if (this.renderer === null) {
      return;
    }

    this.renderer.destroy();
    this.renderer = null;
  }
}
