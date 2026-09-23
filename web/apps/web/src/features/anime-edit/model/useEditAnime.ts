import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  deleteAnime,
  updateAnime,
} from "../../../entities/anime/api/animes";
import type { CreateAnimeInput } from "../../../entities/anime/model/types";

type AnimeEditInput = Partial<Omit<CreateAnimeInput, "episodes">>;

export function useUpdateAnime(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AnimeEditInput) => updateAnime(animeId, input),
    onSuccess: async (anime) => {
      queryClient.setQueryData(["animes", animeId], anime);
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
    },
  });
}

export function useDeleteAnime(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => deleteAnime(animeId),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ["animes", animeId] });
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
    },
  });
}
