import { queryOptions, useQuery } from "@tanstack/react-query";
import { listDownloadJobs } from "../../../entities/download/api/downloadJobs";
import type {
  DownloadJobListParams,
  DownloadJobListResponse,
  DownloadJobStatus,
} from "../../../entities/download/model/types";

export const activeDownloadStatuses = [
  "pending",
  "downloading",
  "paused",
] as const satisfies readonly DownloadJobStatus[];

export const terminalDownloadStatuses = [
  "completed",
  "failed",
  "cancelled",
] as const satisfies readonly DownloadJobStatus[];

export const historyDownloadStatuses = [
  "completed",
  "cancelled",
] as const satisfies readonly DownloadJobStatus[];

export const failedDownloadStatuses = [
  "failed",
] as const satisfies readonly DownloadJobStatus[];

const pollableDownloadStatuses = [
  "pending",
  "downloading",
] as const satisfies readonly DownloadJobStatus[];

type QueryOptions = {
  statuses: readonly DownloadJobStatus[];
  enabled?: boolean;
  page?: number;
};

export function getDownloadJobsRefetchInterval(
  data: DownloadJobListResponse | undefined,
  statuses: readonly DownloadJobStatus[],
): number | false {
  const canPoll = statuses.some((status) =>
    pollableDownloadStatuses.includes(status as (typeof pollableDownloadStatuses)[number]),
  );
  if (!canPoll) {
    return false;
  }

  return data?.items.some((item) =>
    pollableDownloadStatuses.includes(
      item.status as (typeof pollableDownloadStatuses)[number],
    ),
  )
    ? 2000
    : false;
}

export function downloadJobsQueryOptions({
  statuses,
  enabled = true,
  page = 1,
}: QueryOptions) {
  const normalizedStatuses = [...statuses];
  const params: DownloadJobListParams = {
    statuses: normalizedStatuses,
    page,
    pageSize: 100,
  };

  return queryOptions({
    queryKey: [
      "download-jobs",
      "list",
      { statuses: normalizedStatuses, page },
    ] as const,
    queryFn: ({ signal }) => listDownloadJobs({ ...params, signal }),
    enabled,
    refetchOnWindowFocus: false,
    refetchInterval: (query) =>
      getDownloadJobsRefetchInterval(query.state.data, normalizedStatuses),
  });
}

export function useDownloadJobs(options: QueryOptions) {
  return useQuery(downloadJobsQueryOptions(options));
}
