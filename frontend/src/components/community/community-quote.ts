export const COMMUNITY_REPLY_QUOTE_LIMIT = 280;

export function communityReplyQuote(
  authorName: string,
  content: string,
): string {
  const excerptCharacters = Array.from(content.trim());
  const isTruncated = excerptCharacters.length > COMMUNITY_REPLY_QUOTE_LIMIT;
  const excerpt = excerptCharacters
    .slice(0, COMMUNITY_REPLY_QUOTE_LIMIT)
    .join("");
  const quotedLines = excerpt
    .split(/\r?\n/)
    .map((line) => `> ${line}`)
    .join("\n");
  const author = authorName.trim() || "Thành viên";

  return `> ${author} đã viết:\n${quotedLines}${isTruncated ? "…" : ""}\n\n`;
}
