import { queryOptions, useQuery } from "@tanstack/react-query";
import { getPlayback } from "../api/playback";

export function playbackQueryOptions(episodeId: string) {
  return queryOptions({
    queryKey: ["playback", episodeId] as const,
    queryFn: ({ signal }) => getPlayback(episodeId, signal),
  });
}

export function usePlayback(episodeId: string) {
  return useQuery(playbackQueryOptions(episodeId));
}
