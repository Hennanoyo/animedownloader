import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestRelease } from "../../../entities/release/api/ingestRelease";
import type { EpisodeIngestionInput } from "../../../entities/release/model/types";

export function useIngestRelease(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: Omit<EpisodeIngestionInput, "anime_id">) =>
      ingestRelease({ ...input, anime_id: animeId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["animes", animeId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", animeId],
      });
    },
  });
}


import { replaceEpisodeRelease } from "../../../entities/release/api/ingestRelease";
import type { EpisodeReleaseReplacementInput } from "../../../entities/release/model/types";

export function useReplaceRelease(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      episodeId,
      ...input
    }: EpisodeReleaseReplacementInput & { episodeId: string }) =>
      replaceEpisodeRelease(episodeId, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["animes", animeId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", animeId],
      });
    },
  });
}
