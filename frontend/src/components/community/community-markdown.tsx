import type { ReactNode } from "react";

type MarkdownBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "quote"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] };

export function CommunityMarkdown({ content }: { content: string }) {
  const blocks = parseBlocks(content);
  return (
    <div className="community-markdown space-y-5 break-words text-base leading-8 text-[var(--theme-text)]">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const Heading = headingElements[block.level - 1] ?? "h2";
          return (
            <Heading className="font-bold leading-tight" key={`heading-${index}`}>
              {renderInline(block.text)}
            </Heading>
          );
        }
        if (block.type === "paragraph") {
          return <p key={`paragraph-${index}`}>{renderInline(block.text)}</p>;
        }
        if (block.type === "quote") {
          return (
            <blockquote
              className="border-l-2 border-[var(--theme-accent)] pl-4 text-[var(--theme-muted)]"
              key={`quote-${index}`}
              role="blockquote"
            >
              {block.lines.map((line, lineIndex) => (
                <p key={`quote-${index}-${lineIndex}`}>{renderInline(line)}</p>
              ))}
            </blockquote>
          );
        }
        const List = block.ordered ? "ol" : "ul";
        return (
          <List
            aria-label={block.ordered ? "Danh sách có thứ tự" : "Danh sách không thứ tự"}
            className={block.ordered ? "list-decimal space-y-1 pl-7" : "list-disc space-y-1 pl-7"}
            key={`list-${index}`}
          >
            {block.items.map((item, itemIndex) => (
              <li key={`list-${index}-${itemIndex}`}>{renderInline(item)}</li>
            ))}
          </List>
        );
      })}
    </div>
  );
}

const headingElements = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;

function parseBlocks(content: string): MarkdownBlock[] {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1]!.length, text: heading[2]! });
      index += 1;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoted: string[] = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index] ?? "")) {
        quoted.push((lines[index] ?? "").replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", lines: quoted });
      continue;
    }

    const listMatch = /^\s*(?:([-*+])|(\d+)\.)\s+(.+)$/.exec(line);
    if (listMatch) {
      const ordered = Boolean(listMatch[2]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = /^\s*(?:([-*+])|(\d+)\.)\s+(.+)$/.exec(lines[index] ?? "");
        if (!item || Boolean(item[2]) !== ordered) break;
        items.push(item[3]!);
        index += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length) {
      const current = lines[index] ?? "";
      if (
        !current.trim() ||
        /^(#{1,6})\s+/.test(current) ||
        /^\s*>\s?/.test(current) ||
        /^\s*(?:[-*+]\s+|\d+\.\s+)/.test(current)
      ) {
        break;
      }
      paragraph.push(current);
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokenPattern = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = tokenPattern.exec(text)) !== null) {
    const token = match[0];
    const start = match.index;
    if (start > cursor) nodes.push(text.slice(cursor, start));

    if (token.startsWith("**")) {
      nodes.push(<strong key={`inline-${key++}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*")) {
      nodes.push(<em key={`inline-${key++}`}>{token.slice(1, -1)}</em>);
    } else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = link ? safeMarkdownHref(link[2]!) : null;
      if (link && href) {
        nodes.push(
          <a
            className="text-[var(--theme-accent)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
            href={href}
            key={`inline-${key++}`}
            rel={/^https?:\/\//i.test(href) ? "noreferrer noopener" : undefined}
            target={/^https?:\/\//i.test(href) ? "_blank" : undefined}
          >
            {link[1]}
          </a>,
        );
      } else if (link) {
        nodes.push(link[1]);
      } else {
        nodes.push(token);
      }
    }
    cursor = start + token.length;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

function safeMarkdownHref(value: string): string | null {
  const href = value.trim();
  if (!href || /[\\\u0000-\u001f\u007f]/.test(href) || href.startsWith("//")) {
    return null;
  }
  const hasScheme = /^[a-z][a-z\d+.-]*:/i.test(href);
  if (hasScheme && !/^https?:\/\//i.test(href)) return null;
  try {
    const parsed = new URL(href, "https://community.invalid");
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    if (!hasScheme && parsed.origin !== "https://community.invalid") return null;
    return href;
  } catch {
    return null;
  }
}
