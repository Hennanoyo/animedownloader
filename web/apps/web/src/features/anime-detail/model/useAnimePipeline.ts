import { queryOptions, useQuery } from "@tanstack/react-query";
import { getAnimePipeline } from "../../../entities/anime/api/pipeline";

export function animePipelineQueryOptions(animeId: string) {
  return queryOptions({
    queryKey: ["anime-pipelines", animeId] as const,
    queryFn: ({ signal }) => getAnimePipeline(animeId, signal),
    refetchOnMount: "always",
    refetchOnWindowFocus: false,
    refetchInterval: (query) =>
      query.state.data?.episodes.some((episode) => episode.active)
        ? 2000
        : false,
  });
}

export function useAnimePipeline(animeId: string) {
  return useQuery(animePipelineQueryOptions(animeId));
}
