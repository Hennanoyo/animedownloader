export interface Release {
  source: string;
  id: string;
  title: string;
  page_url: string;
  torrent_url: string;
  published_at: Date | null;
  size: string | null;
  seeders: number | null;
  leechers: number | null;
  downloads: number | null;
  info_hash: string | null;
}

export interface ReleaseSearchResponse {
  query: string;
  items: Release[];
}


export type ReleaseParseStatus = "parsed" | "ambiguous" | "unparsed" | "unsupported";

export interface ParsedRelease {
  provider_source: string;
  source_id: string;
  original_title: string;
  normalized_title: string;
  release_group: string | null;
  series_title: string | null;
  episode_number: number | null;
  episode_title: string | null;
  season_number: number | null;
  resolution: string | null;
  source: string | null;
  video_codec: string | null;
  audio_codec: string | null;
  bit_depth: number | null;
  status: ReleaseParseStatus;
  warnings: string[];
  failed_required_fields: string[];
  parser_profile_version: number | null;
}

export interface ReleaseDiscoveryItem {
  release: Release;
  parsed: ParsedRelease;
}

export interface ReleaseDiscoveryResponse {
  query: string;
  warnings: string[];
  search_profile_version: number | null;
  items: ReleaseDiscoveryItem[];
}

export const searchFields = [
  "group",
  "title",
  "episode",
  "resolution",
  "codec",
] as const;
export type SearchField = (typeof searchFields)[number];

export interface ReleaseDiscoveryInput {
  title: string;
  fields: SearchField[];
  group?: string;
  episode?: number;
  resolution?: string;
  codec?: string;
}
