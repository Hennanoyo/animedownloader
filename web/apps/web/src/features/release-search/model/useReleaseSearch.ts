import {
  queryOptions,
  useQuery,
} from "@tanstack/react-query";
import { searchReleases } from "../../../entities/release/api/searchReleases";

export function releaseSearchQueryOptions(query: string) {
  return queryOptions({
    queryKey: ["releases", "search", query] as const,
    queryFn: async ({ signal }) => {
      try {
        return await searchReleases(query, signal);
      } catch (error) {
        if (!signal.aborted) {
          console.error("Release search failed", error);
        }
        throw error;
      }
    },
    enabled: query.length > 0,
    retry: false,
  });
}

export function useReleaseSearch(query: string) {
  return useQuery(releaseSearchQueryOptions(query));
}
