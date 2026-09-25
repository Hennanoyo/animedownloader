from uuid import UUID


class ReleaseGroupNotFoundError(LookupError):
    def __init__(self, group_id: UUID) -> None:
        super().__init__(f"release group not found: {group_id}")


class ReleaseParserProfileNotFoundError(LookupError):
    def __init__(self, profile_id: UUID) -> None:
        super().__init__(f"release parser profile not found: {profile_id}")


class ReleaseParserSampleNotFoundError(LookupError):
    def __init__(self, sample_id: UUID) -> None:
        super().__init__(f"release parser sample not found: {sample_id}")


class ReleaseParserObservationNotFoundError(LookupError):
    def __init__(self, observation_id: UUID) -> None:
        super().__init__(f"release parser observation not found: {observation_id}")


class InvalidReleaseParserProfileError(ValueError):
    pass


class ReleaseParserProfileActivationError(ValueError):
    pass
