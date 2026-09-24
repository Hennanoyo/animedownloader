import { z } from "zod";
import { getJson } from "../../../shared/api/client";
import type { AnimePipeline, PipelineStageStatus } from "../model/pipeline";

const stageStatusSchema: z.ZodType<PipelineStageStatus> = z.enum([
  "not_started",
  "pending",
  "processing",
  "downloading",
  "completed",
  "failed",
  "paused",
  "cancelled",
]);

const currentStageSchema = z.enum([
  "download",
  "processing",
  "preview",
  "streaming",
]);

const pipelineSchema = z.object({
  episode_id: z.uuid(),
  episode_number: z.number().int().positive(),
  title: z.string(),
  download: z.object({
    status: stageStatusSchema,
    downloaded_bytes: z.number().int().nonnegative(),
    total_bytes: z.number().int().nonnegative().nullable(),
    error_message: z.string().nullable(),
  }),
  processing: z.object({
    status: stageStatusSchema,
    progress_percent: z.number().int().min(0).max(100),
    playable_ready: z.boolean(),
    error_message: z.string().nullable(),
  }),
  subtitles: stageStatusSchema,
  attachments: stageStatusSchema,
  streaming: z.object({
    status: stageStatusSchema,
    hls_ready: z.boolean(),
    dash_ready: z.boolean(),
    error_message: z.string().nullable(),
  }),
  thumbnail: z.object({
    status: stageStatusSchema,
    progress_percent: z.number().int().min(0).max(100),
    url: z.url().nullable(),
    vtt_url: z.url().nullable(),
    error_message: z.string().nullable(),
  }),
  current_stage: currentStageSchema.nullable(),
  playback_ready: z.boolean(),
  active: z.boolean(),
});

const animePipelineSchema = z.object({
  anime_id: z.uuid(),
  episodes: z.array(pipelineSchema),
});

export class AnimePipelineResponseError extends Error {
  constructor(readonly issues: z.core.$ZodIssue[]) {
    super(
      "Invalid anime pipeline API response: " +
        issues
          .map(
            (issue) =>
              (issue.path.join(".") || "<root>") + ": " + issue.message,
          )
          .join("; "),
    );
    this.name = "AnimePipelineResponseError";
  }
}

export async function getAnimePipeline(
  animeId: string,
  signal?: AbortSignal,
): Promise<AnimePipeline> {
  const result = animePipelineSchema.safeParse(
    await getJson("/api/animes/" + animeId + "/pipeline", { signal }),
  );
  if (!result.success) {
    throw new AnimePipelineResponseError(result.error.issues);
  }
  return result.data;
}
