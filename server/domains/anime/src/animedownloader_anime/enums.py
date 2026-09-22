from enum import StrEnum


class Season(StrEnum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class DownloadStatus(StrEnum):
    NOT_STARTED = "not_started"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionStatus(StrEnum):
    NOT_STARTED = "not_started"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"
