import { queryOptions, useQuery } from "@tanstack/react-query";
import { discoverReleases } from "../../../entities/release/api/discoverReleases";
import type { ReleaseDiscoveryInput } from "../../../entities/release/model/types";

export function releaseDiscoveryQueryOptions(
  input: ReleaseDiscoveryInput | null,
) {
  return queryOptions({
    queryKey: ["releases", "discover", input] as const,
    queryFn: ({ signal }) => {
      if (input === null) throw new Error("Release discovery input is missing");
      return discoverReleases(input, signal);
    },
    enabled: input !== null,
    retry: false,
  });
}

export function useReleaseDiscovery(input: ReleaseDiscoveryInput | null) {
  return useQuery(releaseDiscoveryQueryOptions(input));
}
