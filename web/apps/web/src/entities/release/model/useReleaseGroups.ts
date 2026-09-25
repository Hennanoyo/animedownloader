import { queryOptions, useQuery } from "@tanstack/react-query";
import { getReleaseGroups } from "../api/releaseProfiles";

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
