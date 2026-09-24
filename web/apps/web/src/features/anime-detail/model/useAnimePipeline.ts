import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  getAnimePipeline,
  retryEpisodePipeline,
} from "../../../entities/anime/api/pipeline";

export function getAnimePipelineRefetchInterval(
  data: { episodes: readonly { active: boolean }[] } | undefined,
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

export function useRetryEpisodePipeline(episodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => retryEpisodePipeline(episodeId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "latest", episodeId],
      });
    },
  });
}
