import { z } from "zod";
import { getJson } from "../../../shared/api/client";
import { playbackSchema, type Playback } from "../model/types";

export class PlaybackResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid playback API response: " +
        issues
          .map(
            (issue) =>
              (issue.path.join(".") || "<root>") + ": " + issue.message,
          )
          .join("; "),
    );
    this.name = "PlaybackResponseError";
  }
}

export async function getPlayback(
  episodeId: string,
  signal?: AbortSignal,
): Promise<Playback> {
  const payload = await getJson("/api/episodes/" + episodeId + "/playback", {
    signal,
  });
  const result = playbackSchema.safeParse(payload);
  if (!result.success) {
    throw new PlaybackResponseError(result.error.issues);
  }
  return result.data;
}
