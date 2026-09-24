export interface ThumbnailCue {
  start_seconds: number;
  end_seconds: number;
  url: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export function parseThumbnailVtt(input: string): ThumbnailCue[] {
  const lines = input.replace(/\r/g, "").split("\n");
  const cues: ThumbnailCue[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const timestamp = lines[index]?.match(
      /^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})$/,
    );
    if (!timestamp) {
      continue;
    }

    const resource = lines[index + 1];
    if (!resource) {
      continue;
    }

    const parsed = resource.match(
      /^(.+?)#xywh=(\d+),(\d+),(\d+),(\d+)$/,
    );
    if (!parsed) {
      continue;
    }

    cues.push({
      start_seconds: parseTimestamp(timestamp[1]),
      end_seconds: parseTimestamp(timestamp[2]),
      url: parsed[1],
      x: Number(parsed[2]),
      y: Number(parsed[3]),
      width: Number(parsed[4]),
      height: Number(parsed[5]),
    });
    index += 1;
  }

  return cues;
}

export function findThumbnailCue(
  cues: ThumbnailCue[],
  seconds: number,
): ThumbnailCue | null {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return null;
  }

  return (
    cues.find(
      (cue) => seconds >= cue.start_seconds && seconds < cue.end_seconds,
    ) ??
    cues.at(-1) ??
    null
  );
}

function parseTimestamp(value: string): number {
  const [hours, minutes, seconds] = value.split(":");
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds);
}
