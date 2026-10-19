export type HighlightSegment = { text: string; matched: boolean };

export function normalizeGuideSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLocaleLowerCase("vi")
    .trim()
    .replace(/\s+/g, " ");
}

export function getHighlightedSegments(
  value: string,
  query: string,
): HighlightSegment[] {
  const normalizedQuery = normalizeGuideSearch(query);
  if (!normalizedQuery) return [{ text: value, matched: false }];

  const normalized = normalizeGuideSearchWithOffsets(value);
  const ranges: Array<[number, number]> = [];
  let from = 0;
  while (from < normalized.text.length) {
    const foundAt = normalized.text.indexOf(normalizedQuery, from);
    if (foundAt < 0) break;
    const first = normalized.offsets[foundAt];
    const last = normalized.offsets[foundAt + normalizedQuery.length - 1];
    if (first !== undefined && last !== undefined) {
      ranges.push([first[0], last[1]]);
    }
    from = foundAt + normalizedQuery.length;
  }

  if (!ranges.length) return [{ text: value, matched: false }];
  const segments: HighlightSegment[] = [];
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (start > cursor)
      segments.push({ text: value.slice(cursor, start), matched: false });
    segments.push({ text: value.slice(start, end), matched: true });
    cursor = end;
  }
  if (cursor < value.length)
    segments.push({ text: value.slice(cursor), matched: false });
  return segments;
}

export function toGuideHeadingId(value: string, occurrence = 1): string {
  const base =
    normalizeGuideSearch(value)
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "section";
  return occurrence > 1 ? `${base}-${occurrence}` : base;
}

function normalizeGuideSearchWithOffsets(value: string): {
  text: string;
  offsets: Array<[number, number]>;
} {
  let text = "";
  const offsets: Array<[number, number]> = [];
  for (let index = 0; index < value.length; ) {
    const point = value.codePointAt(index);
    if (point === undefined) break;
    const source = String.fromCodePoint(point);
    const start = index;
    index += source.length;
    const normalized = source
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/gi, "d")
      .toLocaleLowerCase("vi");
    for (const character of normalized) {
      text += character;
      offsets.push([start, index]);
    }
  }
  return { text, offsets };
}
