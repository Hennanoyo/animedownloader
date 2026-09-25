import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createReleaseGroup,
  getReleaseGroups,
} from "../api/releaseProfiles";

export function releaseGroupsQueryOptions() {
  return queryOptions({
    queryKey: ["release-groups"] as const,
    queryFn: ({ signal }) => getReleaseGroups(signal),
    staleTime: 60_000,
  });
}

export function useReleaseGroups() {
  return useQuery(releaseGroupsQueryOptions());
}

export function useCreateReleaseGroup() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; slug?: string }) =>
      createReleaseGroup(input),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["release-groups"] });
    },
  });
}
