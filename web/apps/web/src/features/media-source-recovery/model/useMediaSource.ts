import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteMediaSourceOrphan,
  getEpisodeMediaSource,
  reprocessEpisodeMediaSource,
  redownloadEpisodeMediaSource,
  selectEpisodeMediaSource,
} from "../../../entities/media-source/api/mediaSource";

export function useEpisodeMediaSource(
  episodeId: string,
  enabled = false,
) {
  return useQuery({
    queryKey: ["media-sources", episodeId] as const,
    queryFn: ({ signal }) => getEpisodeMediaSource(episodeId, signal),
    enabled,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}

function invalidateMediaSourceQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  episodeId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ["media-sources", episodeId],
  });
  void queryClient.invalidateQueries({
    queryKey: ["anime-pipelines"],
  });
  void queryClient.invalidateQueries({
    queryKey: ["download-jobs", "latest", episodeId],
  });
}

export function useReprocessEpisodeMediaSource(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => reprocessEpisodeMediaSource(episodeId),
    onSuccess: () => invalidateMediaSourceQueries(queryClient, episodeId),
  });
}

export function useRedownloadEpisodeMediaSource(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => redownloadEpisodeMediaSource(episodeId),
    onSuccess: () => invalidateMediaSourceQueries(queryClient, episodeId),
  });
}

export function useSelectEpisodeMediaSource(episodeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (path: string) => selectEpisodeMediaSource(episodeId, path),
    onSuccess: () => invalidateMediaSourceQueries(queryClient, episodeId),
  });
}

export function useDeleteMediaSourceOrphan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (directoryId: string) => deleteMediaSourceOrphan(directoryId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["media-source-orphans"],
      });
    },
  });
}

export function useMediaSourceOrphans(enabled = false) {
  return useQuery({
    queryKey: ["media-source-orphans"] as const,
    queryFn: ({ signal }) => import("../../../entities/media-source/api/mediaSource")
      .then(({ listMediaSourceOrphans }) => listMediaSourceOrphans(signal)),
    enabled,
    refetchOnWindowFocus: false,
  });
}
