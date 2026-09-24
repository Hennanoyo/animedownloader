import Hls from "hls.js";
import { DashVideoEngine } from "./dash";
import { HlsVideoEngine } from "./hls";
import { NativeVideoEngine } from "./native";
import type {
  SelectedVideoSource,
  VideoEngine,
  VideoSourceSet,
} from "./types";

export interface SelectedVideoEngine {
  engine: VideoEngine;
  source: SelectedVideoSource;
}

export function selectVideoEngine(
  video: HTMLVideoElement,
  sources: VideoSourceSet,
): SelectedVideoEngine | null {
  if (sources.hls) {
    if (Hls.isSupported()) {
      return {
        engine: new HlsVideoEngine(),
        source: { kind: "hls", source: sources.hls },
      };
    }

    if (video.canPlayType(sources.hls.mime_type)) {
      return {
        engine: new NativeVideoEngine(),
        source: { kind: "hls", source: sources.hls },
      };
    }
  }

  if (
    sources.dash &&
    typeof window !== "undefined" &&
    "MediaSource" in window
  ) {
    return {
      engine: new DashVideoEngine(),
      source: { kind: "dash", source: sources.dash },
    };
  }

  if (sources.direct) {
    return {
      engine: new NativeVideoEngine(),
      source: { kind: "direct", source: sources.direct },
    };
  }

  return null;
}
