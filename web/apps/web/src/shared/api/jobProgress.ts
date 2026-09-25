import { z } from "zod";
import { apiBaseUrl } from "../config/env";

const jobProgressEventSchema = z.object({
  version: z.literal(1),
  type: z.literal("job.progress"),
  job_type: z.string().min(1),
  job_id: z.uuid(),
  status: z.string().min(1),
  progress_percent: z.number().min(0).max(100).nullable(),
  downloaded_bytes: z.number().int().nonnegative().nullable(),
  total_bytes: z.number().int().nonnegative().nullable(),
  error_message: z.string().max(2000).nullable(),
  emitted_at: z.coerce.date(),
});

const jobProgressReadyEventSchema = z.object({
  version: z.literal(1),
  type: z.literal("job.ready"),
  job_type: z.string().min(1),
  emitted_at: z.coerce.date(),
});

export const jobRealtimeMessageSchema = z.discriminatedUnion("type", [
  jobProgressEventSchema,
  jobProgressReadyEventSchema,
]);

export type JobProgressEvent = z.infer<typeof jobProgressEventSchema>;
export type JobProgressReadyEvent = z.infer<
  typeof jobProgressReadyEventSchema
>;
export type JobRealtimeMessage = z.infer<typeof jobRealtimeMessageSchema>;

export function createJobProgressWebSocketUrl(jobType?: string): string {
  const url = new URL("/api/job-events/ws", apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  if (jobType !== undefined) {
    url.searchParams.set("job_type", jobType);
  }
  return url.toString();
}
