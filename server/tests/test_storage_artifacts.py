from uuid import uuid7

import pytest
from animedownloader_storage import (
    AttachmentArtifact,
    FontArtifact,
    PlayableArtifact,
    StreamingPackageArtifact,
    SubtitleArtifact,
    ThumbnailArtifact,
)
from pydantic import ValidationError


def test_playable_artifact_uses_variant_identity() -> None:
    asset_id = uuid7()
    variant_id = uuid7()
    artifact = PlayableArtifact(asset_id=asset_id, variant_id=variant_id)

    assert artifact.filename == f"{variant_id}.mp4"
    assert artifact.object_key == f"playable/{asset_id}/{variant_id}.mp4"
    assert artifact.model_dump()["object_key"] == artifact.object_key


def test_subtitle_artifact_uses_track_identity_and_normalizes_extension() -> None:
    artifact = SubtitleArtifact(
        asset_id=uuid7(),
        track_id=uuid7(),
        extension=".ASS",
    )

    assert artifact.filename == f"{artifact.track_id}.ass"
    assert artifact.object_key == f"subtitles/{artifact.asset_id}/{artifact.track_id}.ass"


def test_attachment_artifact_does_not_depend_on_original_filename() -> None:
    artifact = AttachmentArtifact(
        asset_id=uuid7(),
        attachment_id=uuid7(),
        extension="TTF",
    )

    assert artifact.filename == f"{artifact.attachment_id}.ttf"
    assert artifact.object_key == (f"attachments/{artifact.asset_id}/{artifact.attachment_id}.ttf")


def test_font_artifact_is_content_addressed() -> None:
    sha256 = "A" * 64
    artifact = FontArtifact(sha256=sha256, extension=".TTF")

    assert artifact.sha256 == "a" * 64
    assert artifact.filename == f"{'a' * 64}.ttf"
    assert artifact.object_key == f"fonts/aa/{'a' * 64}.ttf"


@pytest.mark.parametrize("value", ["", ".", "..", "../ttf", "/absolute", "a/b"])
def test_artifacts_reject_invalid_extensions(value: str) -> None:
    with pytest.raises(ValidationError):
        AttachmentArtifact(
            asset_id=uuid7(),
            attachment_id=uuid7(),
            extension=value,
        )


def test_thumbnail_artifact_uses_semantic_filename() -> None:
    asset_id = uuid7()

    sprite = ThumbnailArtifact(asset_id=asset_id, kind="sprite")
    vtt = ThumbnailArtifact(asset_id=asset_id, kind="vtt")

    assert sprite.object_key == f"thumbnails/{asset_id}/sprite.jpg"
    assert vtt.object_key == f"thumbnails/{asset_id}/sprite.vtt"


def test_streaming_package_artifact_matches_package_layout() -> None:
    package_id = uuid7()
    artifact = StreamingPackageArtifact(package_id=package_id)

    assert artifact.object_prefix == f"streaming/{package_id}"
    assert artifact.master_playlist_key == f"streaming/{package_id}/master.m3u8"
    assert artifact.dash_manifest_key == f"streaming/{package_id}/manifest.mpd"
    assert artifact.representation_key("1080p", "index.m3u8") == (
        f"streaming/{package_id}/1080p/index.m3u8"
    )
    assert artifact.segment_key("1080p", "00000.m4s") == (
        f"streaming/{package_id}/1080p/s/00000.m4s"
    )


@pytest.mark.parametrize("quality, filename", [("../1080p", "index.m3u8"), ("1080p", "../x")])
def test_streaming_artifact_rejects_path_traversal(quality: str, filename: str) -> None:
    artifact = StreamingPackageArtifact(package_id=uuid7())

    with pytest.raises(ValueError):
        artifact.representation_key(quality, filename)
