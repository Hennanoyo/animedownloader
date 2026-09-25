import { useEffect, useState } from "react";
import {
  jobRealtimeMessageSchema,
  type JobProgressEvent,
} from "./jobProgress";

const reconnectDelays = [500, 1000, 2000, 4000, 8000, 15000];

interface UseJobProgressRealtimeOptions {
  enabled: boolean;
  jobType?: string;
  onReady?: () => Promise<void> | void;
  onEvent: (event: JobProgressEvent) => void;
}

export function useJobProgressRealtime({
  enabled,
  jobType,
  onReady,
  onEvent,
}: UseJobProgressRealtimeOptions): { connected: boolean } {
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

      socket = new WebSocket(createJobProgressWebSocketUrl(jobType));

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
          void Promise.resolve(onReady?.())
            .then(() => {
              if (!stopped) {
                setConnected(true);
              }
            })
            .catch(() => {
              if (!stopped) {
                setConnected(false);
                socket?.close();
              }
            });
          return;
        }

        onEvent(result.data);
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
  }, [enabled, jobType, onEvent, onReady]);

  return { connected };
}

function createJobProgressWebSocketUrl(jobType?: string): string {
  const url = new URL("/api/job-events/ws", window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  if (jobType !== undefined) {
    url.searchParams.set("job_type", jobType);
  }
  return url.toString();
}
