const widths = [320, 640, 960, 1280, 1600] as const;

export function isCloudinaryPublicImage(src: string | null): src is string {
  if (!src) return false;
  try {
    const url = new URL(src);
    return (
      url.protocol === "https:" &&
      url.hostname === "res.cloudinary.com" &&
      url.pathname.includes("/image/upload/")
    );
  } catch {
    return false;
  }
}

export function cloudinaryPublicImageLoader({
  src,
  width,
}: {
  src: string;
  width: number;
}): string {
  const chosenWidth = widths.find((candidate) => candidate >= width) ?? 1600;
  const marker = "/image/upload/";
  const [prefix, path] = src.split(marker, 2);
  if (!path) return src;
  const source = path.startsWith("c_limit,")
    ? path.slice(path.indexOf("/") + 1)
    : path;
  return `${prefix}${marker}c_limit,w_${chosenWidth},q_auto,f_auto/${source}`;
}

export function isCloudinaryPublicPoster(src: string | null): src is string {
  if (!src) return false;
  try {
    const url = new URL(src);
    return (
      url.protocol === "https:" &&
      url.hostname === "res.cloudinary.com" &&
      /\/video\/upload\/so_[^/]+\/v\d+\//.test(url.pathname)
    );
  } catch {
    return false;
  }
}

export function cloudinaryPublicPosterLoader({
  src,
  width,
}: {
  src: string;
  width: number;
}): string {
  if (!isCloudinaryPublicPoster(src)) return src;
  const chosenWidth = widths.find((candidate) => candidate >= width) ?? 1600;
  return src.replace(
    /(\/video\/upload\/)(so_[^/,]+)[^/]*(\/v\d+\/)/,
    `$1$2,c_limit,w_${chosenWidth},q_auto:eco,f_webp$3`,
  );
}
