# Media fixture

Generate the deterministic media fixture with FFmpeg:

```sh
python3 server/tests/fixtures/media/generate.py /tmp/animedownloader-fixture.mkv
```

The fixture contains:

- a 12-second 320x180 video
- AAC audio
- an ASS subtitle track
- three chapters
- one tiny embedded font attachment

The attachment bytes are intentionally synthetic. They are used to exercise Matroska attachment extraction and content-addressed storage; the fixture is not intended to test font rendering.
