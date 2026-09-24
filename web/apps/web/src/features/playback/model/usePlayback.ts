import { queryOptions, useQuery } from "@tanstack/react-query";
import { getPlayback } from "../api/playback";

export function playbackQueryOptions(episodeId: string) {
  return queryOptions({
    queryKey: ["playback", episodeId] as const,
    queryFn: ({ signal }) => getPlayback(episodeId, signal),
    retry: 1,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function usePlayback(episodeId: string) {
  return useQuery(playbackQueryOptions(episodeId));
}
