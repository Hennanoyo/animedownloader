export const seasons = ["winter", "spring", "summer", "fall"] as const;

export const animeTitleKinds = ["romaji", "jp", "ko", "en"] as const;
export type AnimeTitleKind = (typeof animeTitleKinds)[number];
export type AnimeTitles = Partial<Record<AnimeTitleKind, string>>;
export type Season = (typeof seasons)[number];

export const weekdays = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;
export type Weekday = (typeof weekdays)[number];

export const downloadStatuses = [
  "not_started",
  "downloading",
  "completed",
  "failed",
] as const;
export type DownloadStatus = (typeof downloadStatuses)[number];

export const conversionStatuses = [
  "not_started",
  "converting",
  "completed",
  "failed",
] as const;
export type ConversionStatus = (typeof conversionStatuses)[number];

export interface Episode {
  id: string;
  anime_id: string;
  episode_number: number;
  title: string;
  source: string;
  source_id: string | null;
  source_title: string | null;
  source_url: string | null;
  torrent_url: string;
  size: string | null;
  seeders: number | null;
  leechers: number | null;
  downloads: number | null;
  info_hash: string | null;
  download_status: DownloadStatus;
  conversion_status: ConversionStatus;
  created_at: Date;
  updated_at: Date;
}

export interface Anime {
  id: string;
  title: string;
  titles: AnimeTitles;
  year: number;
  season: Season;
  weekday: Weekday;
  air_time: string | null;
  timezone: string;
  created_at: Date;
  updated_at: Date;
  episodes: Episode[];
}

export interface EpisodeInput {
  episode_number: number;
  title: string;
  source: string;
  source_id?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  torrent_url: string;
  size?: string | null;
  seeders?: number | null;
  leechers?: number | null;
  downloads?: number | null;
  info_hash?: string | null;
  download_status?: DownloadStatus;
  conversion_status?: ConversionStatus;
}

export interface CreateAnimeInput {
  title: string;
  titles: AnimeTitles;
  year: number;
  season: Season;
  weekday: Weekday;
  air_time?: string | null;
  timezone: string;
  episodes: EpisodeInput[];
}
