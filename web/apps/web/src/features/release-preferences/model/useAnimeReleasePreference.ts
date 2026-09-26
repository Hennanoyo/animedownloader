import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAnimeReleasePreference,
  updateAnimeReleasePreference,
  type AnimeReleasePreferenceInput,
} from "../../../entities/anime/api/releasePreferences";

export function animeReleasePreferenceQueryOptions(animeId: string) {
  return queryOptions({
    queryKey: ["anime-release-preference", animeId] as const,
    queryFn: ({ signal }) => getAnimeReleasePreference(animeId, signal),
    staleTime: 60_000,
  });
}

export function useAnimeReleasePreference(animeId: string) {
  return useQuery(animeReleasePreferenceQueryOptions(animeId));
}

export function useUpdateAnimeReleasePreference(animeId: string) {
  const client = useQueryClient();

  return useMutation({
    mutationFn: (input: AnimeReleasePreferenceInput) =>
      updateAnimeReleasePreference(animeId, input),
    onSuccess: async (preference) => {
      client.setQueryData(
        ["anime-release-preference", animeId],
        preference,
      );
      await client.invalidateQueries({
        queryKey: ["releases", "discover"],
      });
    },
  });
}
