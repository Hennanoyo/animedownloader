import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getReleaseAutomationPolicy,
  previewReleaseAutomation,
  runReleaseAutomation,
  updateReleaseAutomationPolicy,
  type ReleaseAutomationPolicyInput,
} from "../../../entities/anime/api/releaseAutomation";

export function useReleaseAutomationPolicy(animeId: string) {
  return useQuery({
    queryKey: ["release-automation-policy", animeId],
    queryFn: ({ signal }) => getReleaseAutomationPolicy(animeId, signal),
    staleTime: 30_000,
  });
}

export function useUpdateReleaseAutomationPolicy(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: ReleaseAutomationPolicyInput) =>
      updateReleaseAutomationPolicy(animeId, input),
    onSuccess: (data) => {
      queryClient.setQueryData(["release-automation-policy", animeId], data);
    },
  });
}

export function useReleaseAutomationPreview(animeId: string) {
  return useQuery({
    queryKey: ["release-automation-preview", animeId],
    queryFn: ({ signal }) => previewReleaseAutomation(animeId, signal),
    staleTime: 10_000,
  });
}

export function useRunReleaseAutomation(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => runReleaseAutomation(animeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["release-automation-preview", animeId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["release-discovery-candidates"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["animes", animeId],
      });
    },
  });
}
