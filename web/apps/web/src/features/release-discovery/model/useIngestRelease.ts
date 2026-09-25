import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestRelease } from "../../../entities/release/api/ingestRelease";
import type { EpisodeIngestionInput } from "../../../entities/release/model/types";

export function useIngestRelease(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: Omit<EpisodeIngestionInput, "anime_id">) =>
      ingestRelease({ ...input, anime_id: animeId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["anime", animeId] });
      void queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", animeId],
      });
    },
  });
}
