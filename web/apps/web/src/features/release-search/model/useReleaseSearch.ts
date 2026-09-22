import {
  queryOptions,
  useQuery,
} from "@tanstack/react-query";
import { searchReleases } from "../../../entities/release/api/searchReleases";

export function releaseSearchQueryOptions(query: string) {
  return queryOptions({
    queryKey: ["releases", "search", query] as const,
    queryFn: ({ signal }) => searchReleases(query, signal),
    enabled: query.length > 0,
  });
}

export function useReleaseSearch(query: string) {
  return useQuery(releaseSearchQueryOptions(query));
}
