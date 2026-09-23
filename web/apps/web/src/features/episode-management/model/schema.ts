import { z } from "zod";
import type { Release } from "../../../entities/release/model/types";

export interface EpisodeFormValues {
  episode_number: number;
  title: string;
  release: Release | null;
}

const baseSchema = z.object({
  episode_number: z.number().int().min(1).max(9999),
  title: z.string().trim().min(1, "Enter an episode title.").max(300),
  release: z.custom<Release>().nullable(),
});

export const episodeEditFormSchema = baseSchema;

export const episodeCreateFormSchema = baseSchema.superRefine((value, ctx) => {
  if (value.release === null) {
    ctx.addIssue({
      code: "custom",
      path: ["release"],
      message: "Select a Nyaa release.",
    });
  }
});
