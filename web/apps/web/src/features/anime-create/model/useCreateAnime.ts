import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createAnime,
  listAnimes,
} from "../../../entities/anime/api/animes";
import type { CreateAnimeInput } from "../../../entities/anime/model/types";

export function animeListQueryOptions() {
  return queryOptions({
    queryKey: ["animes"] as const,
    queryFn: ({ signal }) => listAnimes(signal),
  });
}

export function useAnimes() {
  return useQuery(animeListQueryOptions());
}

export function useCreateAnime() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateAnimeInput) => createAnime(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
    },
  });
}
