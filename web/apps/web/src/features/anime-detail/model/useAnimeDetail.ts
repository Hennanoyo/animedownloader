import { queryOptions, useQuery } from "@tanstack/react-query";
import { getAnime } from "../../../entities/anime/api/animes";

export function animeDetailQueryOptions(animeId: string) {
  return queryOptions({
    queryKey: ["animes", animeId] as const,
    queryFn: ({ signal }) => getAnime(animeId, signal),
  });
}

export function useAnimeDetail(animeId: string) {
  return useQuery(animeDetailQueryOptions(animeId));
}
