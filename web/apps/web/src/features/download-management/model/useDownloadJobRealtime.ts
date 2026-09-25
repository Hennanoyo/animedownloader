import type { QueryClient } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  createJobProgressWebSocketUrl,
  jobRealtimeMessageSchema,
  type JobProgressEvent,
} from "../../../shared/api/jobProgress";
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

const reconnectDelays = [500, 1000, 2000, 4000, 8000, 15000];

export function useDownloadJobRealtime({ enabled }: { enabled: boolean }) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let stopped = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectAttempt = 0;
    let socket: WebSocket | null = null;

    if (!enabled) {
      setConnected(false);
      return;
    }

    const connect = () => {
      if (stopped) {
        return;
      }

      socket = new WebSocket(createJobProgressWebSocketUrl("download"));

      socket.onopen = () => {
        reconnectAttempt = 0;
      };

      socket.onmessage = (message) => {
        let payload: unknown;
        try {
          payload = JSON.parse(String(message.data));
        } catch {
          return;
        }

        const result = jobRealtimeMessageSchema.safeParse(payload);
        if (!result.success) {
          return;
        }

        if (result.data.type === "job.ready") {
          setConnected(true);
          void queryClient.refetchQueries({
            queryKey: activeDownloadQueryKey,
            type: "active",
          });
          return;
        }

        applyDownloadJobEvent(queryClient, result.data);
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        setConnected(false);
        socket = null;
        if (stopped) {
          return;
        }

        const delay =
          reconnectDelays[Math.min(reconnectAttempt, reconnectDelays.length - 1)];
        reconnectAttempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      stopped = true;
      setConnected(false);
      if (reconnectTimer !== undefined) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
      socket = null;
    };
  }, [enabled, queryClient]);

  return { connected };
}

export function applyDownloadJobEvent(
  queryClient: QueryClient,
  event: JobProgressEvent,
): void {
  if (!isDownloadJobStatus(event.status)) {
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

      if (isTerminalDownloadStatus(event.status)) {
        return {
          ...data,
          items: data.items.filter((item) => item.id !== event.job_id),
          total: Math.max(0, data.total - 1),
        };
      }

      const items = [...data.items];
      const current = items[index];
      items[index] = {
        ...current,
        status: event.status,
        downloaded_bytes:
          event.downloaded_bytes ?? current.downloaded_bytes,
        total_bytes: event.total_bytes ?? current.total_bytes,
        error_message: event.error_message,
        updated_at: event.emitted_at,
      };
      return { ...data, items };
    },
  );

  if (isTerminalDownloadStatus(event.status)) {
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
