const coverWidths = [320, 640, 960, 1280] as const;

export function isPublicCoverImage(src: string | null): src is string {
  return Boolean(
    src?.includes("/api/v1/public/works/") && /[?&]cover=true(?:&|$)/.test(src),
  );
}

export function publicCoverLoader({
  src,
  width,
}: {
  src: string;
  width: number;
}): string {
  const coverWidth =
    coverWidths.find((candidate) => candidate >= width) ?? 1280;
  return `${src}&coverWidth=${coverWidth}`;
}
