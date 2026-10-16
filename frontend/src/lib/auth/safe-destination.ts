export function safeLocalDestination(
  value: string | undefined,
  fallback: string,
): string {
  if (!value) return fallback;

  try {
    if (
      !value.startsWith("/") ||
      value.startsWith("//") ||
      value.includes("\\") ||
      /[\u0000-\u001f\u007f]/.test(value) ||
      /%(?![0-9a-f]{2})/i.test(value)
    )
      return fallback;

    const destination = new URL(value, "https://thv.invalid");
    if (
      destination.origin !== "https://thv.invalid" ||
      !destination.pathname.startsWith("/") ||
      destination.hash
    )
      return fallback;

    const decodedPathname = decodeURIComponent(destination.pathname);
    if (
      decodedPathname.startsWith("//") ||
      decodedPathname.includes("\\") ||
      /[\u0000-\u001f\u007f]/.test(decodedPathname)
    )
      return fallback;

    return `${destination.pathname}${destination.search}`;
  } catch {
    return fallback;
  }
}
