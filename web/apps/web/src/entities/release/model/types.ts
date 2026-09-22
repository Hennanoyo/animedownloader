export interface Release {
  source: string;
  id: string;
  title: string;
  page_url: string;
  torrent_url: string;
  published_at: string | null;
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
