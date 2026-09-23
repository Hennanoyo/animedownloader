import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiRequestError } from "../../../shared/api/client";
import {
  createEpisodeDownloadJob,
  getLatestEpisodeDownloadJob,
} from "../../../entities/download/api/downloadJobs";
import type { DownloadJob } from "../../../entities/download/model/types";

export function episodeDownloadQueryOptions(episodeId: string) {
  return queryOptions({
    queryKey: ["download-jobs", "latest", episodeId] as const,
    queryFn: ({ signal }) => getLatestEpisodeDownloadJob(episodeId, signal),
    refetchInterval: (query) => {
      const job = query.state.data;
      return job?.status === "pending" || job?.status === "downloading"
        ? 2000
        : false;
    },
  });
}

export function useEpisodeDownload(episodeId: string) {
  return useQuery(episodeDownloadQueryOptions(episodeId));
}

export function useCreateEpisodeDownloadJob(episodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => createEpisodeDownloadJob(episodeId),
    onSuccess: async (job) => {
      queryClient.setQueryData(
        ["download-jobs", "latest", episodeId],
        job,
      );
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "latest", episodeId],
      });
    },
    onError: (error) => {
      if (error instanceof ApiRequestError && error.status === 409) {
        void queryClient.invalidateQueries({
          queryKey: ["download-jobs", "latest", episodeId],
        });
      }
    },
  });
}

export type { DownloadJob };
