export interface PlaybackSubtitle {
  id: string;
  language: string | null;
  title: string | null;
  is_default: boolean;
  is_forced: boolean;
  format: string | null;
  url: string;
}

export interface PlaybackFontSource {
  id: string;
  name: string;
  mime_type: string | null;
  url: string;
}
