import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createEpisode,
  deleteEpisode,
  updateEpisode,
} from "../../../entities/anime/api/animes";
import type { Anime, EpisodeInput } from "../../../entities/anime/model/types";

function updateAnimeEpisodes(
  update: (episodes: Anime["episodes"]) => Anime["episodes"],
) {
  return (current: Anime | undefined): Anime | undefined => {
    if (!current) {
      return current;
    }

    return {
      ...current,
      episodes: update(current.episodes),
    };
  };
}

export function useCreateEpisode(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: EpisodeInput) => createEpisode(animeId, input),
    onSuccess: async (episode) => {
      queryClient.setQueryData(
        ["animes", animeId],
        updateAnimeEpisodes((episodes) =>
          [...episodes, episode].sort(
            (left, right) => left.episode_number - right.episode_number,
          ),
        ),
      );
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", animeId],
      });
    },
  });
}

export function useUpdateEpisode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      episodeId,
      input,
    }: {
      episodeId: string;
      input: Partial<EpisodeInput>;
    }) => updateEpisode(episodeId, input),
    onSuccess: async (episode) => {
      queryClient.setQueryData(
        ["animes", episode.anime_id],
        updateAnimeEpisodes((episodes) =>
          episodes
            .map((current) => (current.id === episode.id ? episode : current))
            .sort(
              (left, right) => left.episode_number - right.episode_number,
            ),
        ),
      );
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
    },
  });
}

export function useDeleteEpisode(animeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (episodeId: string) => deleteEpisode(episodeId),
    onSuccess: async (_, episodeId) => {
      queryClient.setQueryData(
        ["animes", animeId],
        updateAnimeEpisodes((episodes) =>
          episodes.filter((episode) => episode.id !== episodeId),
        ),
      );
      await queryClient.invalidateQueries({ queryKey: ["animes"] });
      await queryClient.invalidateQueries({
        queryKey: ["anime-pipelines", animeId],
      });
    },
  });
}
