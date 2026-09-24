import { z } from "zod";

const playbackSourceSchema = z.object({
  url: z.string().url(),
  mime_type: z.string().min(1),
});

const playbackVideoSchema = z.object({
  direct: playbackSourceSchema.nullable(),
  hls: playbackSourceSchema.nullable(),
  dash: playbackSourceSchema.nullable(),
});

const playbackSubtitleSchema = z.object({
  id: z.uuid(),
  language: z.string().nullable(),
  title: z.string().nullable(),
  is_default: z.boolean(),
  is_forced: z.boolean(),
  format: z.string().nullable(),
  url: z.string().url(),
});

const playbackFontSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  mime_type: z.string().nullable(),
  url: z.string().url(),
});

const playbackChapterSchema = z.object({
  id: z.uuid(),
  title: z.string().nullable(),
  start_time_seconds: z.number(),
  end_time_seconds: z.number(),
});

const playbackThumbnailSchema = z.object({
  sprite_url: z.string().url(),
  vtt_url: z.string().url(),
});

export const playbackSchema = z.object({
  episode_id: z.uuid(),
  episode_number: z.number().int().positive(),
  title: z.string(),
  duration_seconds: z.number().nullable(),
  video: playbackVideoSchema.nullable(),
  subtitles: z.array(playbackSubtitleSchema),
  fonts: z.array(playbackFontSchema),
  chapters: z.array(playbackChapterSchema),
  thumbnails: playbackThumbnailSchema.nullable(),
});

export type Playback = z.infer<typeof playbackSchema>;
export type PlaybackSource = z.infer<typeof playbackSourceSchema>;
export type PlaybackVideo = z.infer<typeof playbackVideoSchema>;
