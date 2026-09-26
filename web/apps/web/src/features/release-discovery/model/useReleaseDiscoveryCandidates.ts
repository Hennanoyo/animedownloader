import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acceptReleaseDiscoveryCandidate,
  getReleaseDiscoverySchedule,
  listReleaseDiscoveryCandidates,
  listReleaseDiscoveryRuns,
  runReleaseDiscoveryNow,
  updateReleaseDiscoveryCandidate,
  updateReleaseDiscoverySchedule,
  type ReleaseCandidateStatus,
} from "../../../entities/release/api/discoveryCandidates";

export function useReleaseDiscoveryCandidates(
  params: { animeId?: string; status?: ReleaseCandidateStatus },
) {
  return useQuery({
    queryKey: ["release-discovery-candidates", params],
    queryFn: ({ signal }) => listReleaseDiscoveryCandidates(params, signal),
    staleTime: 15_000,
  });
}

export function useReleaseDiscoveryRuns(animeId?: string) {
  return useQuery({
    queryKey: ["release-discovery-runs", animeId],
    queryFn: ({ signal }) => listReleaseDiscoveryRuns(animeId, signal),
    staleTime: 5_000,
  });
}

export function useReleaseDiscoverySchedule(animeId: string) {
  return useQuery({
    queryKey: ["release-discovery-schedule", animeId],
    queryFn: ({ signal }) => getReleaseDiscoverySchedule(animeId, signal),
    staleTime: 30_000,
  });
}

export function useUpdateReleaseDiscoverySchedule(animeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { enabled: boolean; interval_minutes: number }) =>
      updateReleaseDiscoverySchedule(animeId, input),
    onSuccess: (data) => {
      queryClient.setQueryData(
        ["release-discovery-schedule", animeId],
        data,
      );
    },
  });
}

export function useRunReleaseDiscoveryNow(animeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => runReleaseDiscoveryNow(animeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["release-discovery-runs", animeId],
      });
    },
  });
}

export function useAcceptReleaseDiscoveryCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      candidateId,
      replaceEpisodeId,
    }: {
      candidateId: string;
      replaceEpisodeId?: string;
    }) => acceptReleaseDiscoveryCandidate(candidateId, replaceEpisodeId),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["release-discovery-candidates"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["release-discovery-runs"],
      });
      queryClient.setQueryData(
        ["release-discovery-candidate", data.candidate.id],
        data.candidate,
      );
      void queryClient.invalidateQueries({
        queryKey: ["animes", data.candidate.anime_id],
      });
      void queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", data.candidate.anime_id],
      });
    },
  });
}

export function useUpdateReleaseDiscoveryCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      candidateId,
      status,
    }: {
      candidateId: string;
      status: Exclude<ReleaseCandidateStatus, "accepted">;
    }) => updateReleaseDiscoveryCandidate(candidateId, status),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["release-discovery-candidates"],
      });
      queryClient.setQueryData(
        ["release-discovery-candidate", data.id],
        data,
      );
    },
  });
}
