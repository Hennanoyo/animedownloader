import { z } from "zod";
import type { Release } from "../../../entities/release/model/types";
import type { Season, Weekday } from "../../../entities/anime/model/types";

export interface AnimeEpisodeDraft {
  episode_number: number;
  title: string;
  release: Release | null;
}

export interface AnimeCreateFormValues {
  title: string;
  titles: { romaji: string; jp: string; ko: string; en: string };
  year: number;
  season: Season;
  weekday: Weekday;
  air_time: string;
  timezone: string;
  episodes: AnimeEpisodeDraft[];
}

export const animeCreateFormSchema = z
  .object({
    title: z.string().trim().min(1, "Enter an anime title.").max(200),
    titles: z.object({
      romaji: z.string().trim().max(200),
      jp: z.string().trim().max(200),
      ko: z.string().trim().max(200),
      en: z.string().trim().max(200),
    }),
    year: z.number().int().min(1900).max(2100),
    season: z.enum(["winter", "spring", "summer", "fall"]),
    weekday: z.enum([
      "monday",
      "tuesday",
      "wednesday",
      "thursday",
      "friday",
      "saturday",
      "sunday",
    ]),
    air_time: z
      .string()
      .regex(/^$|^(?:[01]\d|2[0-3]):[0-5]\d$/, "Use HH:MM format."),
    timezone: z.string().trim().min(1).max(64),
    episodes: z.array(
      z.object({
        episode_number: z.number().int().min(1).max(9999),
        title: z.string().trim().min(1).max(300),
        release: z.custom<Release>().nullable(),
      }),
    ),
  })
  .superRefine((value, ctx) => {
    const seen = new Set<number>();

    value.episodes.forEach((episode, index) => {
      if (seen.has(episode.episode_number)) {
        ctx.addIssue({
          code: "custom",
          path: ["episodes", index, "episode_number"],
          message: "Episode number must be unique.",
        });
      }
      seen.add(episode.episode_number);

      if (episode.release === null) {
        ctx.addIssue({
          code: "custom",
          path: ["episodes", index, "release"],
          message: "Select a Nyaa release.",
        });
      }
    });
  });
