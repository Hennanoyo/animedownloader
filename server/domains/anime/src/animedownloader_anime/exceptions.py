class AnimeNotFoundError(LookupError):
    def __init__(self, anime_id: object) -> None:
        super().__init__("Anime " + str(anime_id) + " was not found")


class EpisodeNotFoundError(LookupError):
    def __init__(self, episode_id: object) -> None:
        super().__init__("Episode " + str(episode_id) + " was not found")


class DuplicateEpisodeError(ValueError):
    def __init__(self, episode_number: int) -> None:
        super().__init__("Episode " + str(episode_number) + " already exists")
