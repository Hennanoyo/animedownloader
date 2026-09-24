import { queryOptions, useQuery } from "@tanstack/react-query";
import { getAnimePipeline } from "../../../entities/anime/api/pipeline";

export function getAnimePipelineRefetchInterval(
  data: import("../../../entities/anime/model/pipeline").AnimePipeline | undefined,
): number | false {
  return data?.episodes.some((episode) => episode.active) ? 2000 : false;
}

export function animePipelineQueryOptions(animeId: string) {
  return queryOptions({
    queryKey: ["anime-pipelines", animeId] as const,
    queryFn: ({ signal }) => getAnimePipeline(animeId, signal),
    refetchOnMount: "always",
    refetchOnWindowFocus: false,
    refetchInterval: (query) => getAnimePipelineRefetchInterval(query.state.data),
  });
}

export function useAnimePipeline(animeId: string) {
  return useQuery(animePipelineQueryOptions(animeId));
}
