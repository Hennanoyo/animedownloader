import { z } from "zod";
import type { Season, Weekday } from "../../../entities/anime/model/types";

export interface AnimeEditFormValues {
  title: string;
  year: number;
  season: Season;
  weekday: Weekday;
  air_time: string;
  timezone: string;
}

export const animeEditFormSchema = z.object({
  title: z.string().trim().min(1, "Enter an anime title.").max(200),
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
});
