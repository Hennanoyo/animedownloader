import type { QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { JobProgressEvent } from "../../../shared/api/jobProgress";
import { useJobProgressRealtime } from "../../../shared/api/useJobProgressRealtime";
import type {
  DownloadJobListResponse,
  DownloadJobStatus,
} from "../../../entities/download/model/types";
import {
  activeDownloadStatuses,
  terminalDownloadStatuses,
} from "./useDownloadJobs";

const activeDownloadQueryKey = [
  "download-jobs",
  "list",
  { statuses: [...activeDownloadStatuses], page: 1 },
] as const;

export function useDownloadJobRealtime({ enabled }: { enabled: boolean }) {
  const queryClient = useQueryClient();
  const onReady = useCallback(
    () =>
      queryClient.refetchQueries({
        queryKey: activeDownloadQueryKey,
        type: "active",
      }),
    [queryClient],
  );
  const onEvent = useCallback(
    (event: JobProgressEvent) => {
      applyDownloadJobEvent(queryClient, event);
    },
    [queryClient],
  );

  return useJobProgressRealtime({
    enabled,
    jobType: "download",
    onReady,
    onEvent,
  });
}

export function applyDownloadJobEvent(
  queryClient: QueryClient,
  event: JobProgressEvent,
): void {
  const status = event.status;
  if (!isDownloadJobStatus(status)) {
    return;
  }

  queryClient.setQueryData<DownloadJobListResponse>(
    activeDownloadQueryKey,
    (data) => {
      if (!data) {
        return data;
      }

      const index = data.items.findIndex((item) => item.id === event.job_id);
      if (index < 0) {
        return data;
      }

      if (isTerminalDownloadStatus(status)) {
        return {
          ...data,
          items: data.items.filter((item) => item.id !== event.job_id),
          total: Math.max(0, data.total - 1),
        };
      }

      const items = [...data.items];
      const current = items[index];
      if (event.emitted_at.getTime() <= current.updated_at.getTime()) {
        return data;
      }
      items[index] = {
        ...current,
        status,
        downloaded_bytes:
          event.downloaded_bytes ?? current.downloaded_bytes,
        total_bytes: event.total_bytes ?? current.total_bytes,
        error_message: event.error_message,
        updated_at: event.emitted_at,
      };
      return { ...data, items };
    },
  );

  if (isTerminalDownloadStatus(status)) {
    void queryClient.invalidateQueries({ queryKey: ["download-jobs", "list"] });
  }
}

function isDownloadJobStatus(status: string): status is DownloadJobStatus {
  return [
    "pending",
    "downloading",
    "paused",
    "completed",
    "failed",
    "cancelled",
  ].includes(status);
}

function isTerminalDownloadStatus(
  status: DownloadJobStatus,
): status is (typeof terminalDownloadStatuses)[number] {
  return terminalDownloadStatuses.includes(
    status as (typeof terminalDownloadStatuses)[number],
  );
}
