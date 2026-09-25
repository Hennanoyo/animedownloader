import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiRequestError } from "../../../shared/api/client";
import {
  cancelDownloadJob,
  createEpisodeDownloadJob,
  deleteDownloadJob,
  getLatestEpisodeDownloadJob,
  pauseDownloadJob,
  resumeDownloadJob,
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
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "list"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines"],
      });
    },
    onError: (error) => {
      if (error instanceof ApiRequestError && error.status === 409) {
        void queryClient.invalidateQueries({
          queryKey: ["download-jobs", "latest", episodeId],
        });
        void queryClient.invalidateQueries({
          queryKey: ["download-jobs", "list"],
        });
      }
    },
  });
}

export type { DownloadJob };

function useDownloadJobAction(
  episodeId: string,
  action: (
    jobId: string,
    signal?: AbortSignal,
  ) => Promise<DownloadJob>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => action(jobId),
    onSuccess: async (job) => {
      queryClient.setQueryData(
        ["download-jobs", "latest", episodeId],
        job,
      );
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "latest", episodeId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "list"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines"],
      });
    },
  });
}

export function usePauseDownloadJob(episodeId: string) {
  return useDownloadJobAction(episodeId, pauseDownloadJob);
}

export function useResumeDownloadJob(episodeId: string) {
  return useDownloadJobAction(episodeId, resumeDownloadJob);
}

export function useCancelDownloadJob(episodeId: string) {
  return useDownloadJobAction(episodeId, cancelDownloadJob);
}

export function useDeleteDownloadJob(episodeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => deleteDownloadJob(jobId),
    onSuccess: async () => {
      queryClient.setQueryData(
        ["download-jobs", "latest", episodeId],
        null,
      );
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "latest", episodeId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["download-jobs", "list"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines"],
      });
    },
  });
}
