import { toGuideHeadingId } from "@/components/guide/guide-search";

export type GuideHeading = { id: string; text: string; level: 2 | 3 };
export type GuideFaqItem = { question: string; answer: string };

export function getGuideFaqItems(bodyHtml: string): GuideFaqItem[] {
  const sections = bodyHtml.matchAll(
    /<h2\b[^>]*>([\s\S]*?)<\/h2>([\s\S]*?)(?=<h2\b|$)/gi,
  );
  const entries: GuideFaqItem[] = [];

  for (const section of sections) {
    const title = htmlToPlainText(section[1] ?? "").toLocaleLowerCase("vi");
    if (title !== "câu hỏi thường gặp") continue;

    const questions = (section[2] ?? "").matchAll(
      /<h3\b[^>]*>([\s\S]*?)<\/h3>([\s\S]*?)(?=<h3\b|$)/gi,
    );
    for (const question of questions) {
      const label = htmlToPlainText(question[1] ?? "");
      const answer = htmlToPlainText(question[2] ?? "");
      if (label && answer) entries.push({ question: label, answer });
    }
  }

  return entries;
}

export function prepareGuideArticleBody(bodyHtml: string): {
  html: string;
  headings: GuideHeading[];
} {
  const occurrences = new Map<string, number>();
  const headings: GuideHeading[] = [];
  const customerFacingBody = bodyHtml
    .replace(
      /Người đánh giá gửi kết quả cho quản trị viên xem xét\.\s*Việc gửi kết quả thẩm định không tự quyết định hồ sơ được duyệt hay công bố\./gi,
      "Sau khi gửi, kết quả thẩm định được ghi nhận. Việc gửi kết quả chưa đồng nghĩa hồ sơ đã được duyệt hoặc công bố.",
    )
    .replace(
      /Kết quả được gửi để quản trị viên xem xét;\s*thao tác này không tự quyết định việc duyệt hoặc công bố\./gi,
      "Kết quả đã được gửi; thao tác này chưa đồng nghĩa hồ sơ được duyệt hoặc công bố.",
    )
    .replace(
      /quản trị viên xem kết quả để quyết định bước tiếp theo/gi,
      "trạng thái hồ sơ được cập nhật sau khi kết quả được tiếp nhận",
    )
    .replace(/chờ quản trị viên xử lý/gi, "chờ trạng thái được cập nhật")
    .replace(
      /Quản trị viên chỉ định người và phiên bản hồ sơ;\s*hỏi người phân công nếu việc chưa xuất hiện/gi,
      "Chỉ hồ sơ được giao cho tài khoản của bạn mới xuất hiện; nếu vẫn chưa thấy, liên hệ bộ phận hỗ trợ",
    )
    .replace(
      /Liên hệ quản trị viên để kiểm tra việc phân công\.?/gi,
      "Nếu vẫn chưa thấy, liên hệ bộ phận hỗ trợ.",
    )
    .replace(
      /liên hệ quản trị viên để kiểm tra việc phân công đúng tài khoản/gi,
      "liên hệ bộ phận hỗ trợ để được hướng dẫn",
    )
    .replace(
      /liên hệ người phân công(?: để đối chiếu)?/gi,
      "liên hệ bộ phận hỗ trợ để được hướng dẫn",
    )
    .replace(
      /Bản ghi xác minh dùng để đối chiếu dấu vân tay số và lịch sử ghi nhận\. Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân; bằng xác lập không thay thế kết luận pháp lý hay giấy tờ quyền sở hữu\./gi,
      "Bản xác lập giúp đối chiếu thông tin và lịch sử ghi nhận. Bản xác lập không thay thế kết luận pháp lý hay giấy tờ chứng minh quyền sở hữu.",
    )
    .replace(/dấu vân tay số/gi, "thông tin xác minh")
    .replace(
      /Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân/gi,
      "Bản xác lập không phải nơi lưu trữ hồ sơ gốc",
    )
    .replace(/\bBlockchain\b/gi, "hệ thống")
    .replace(/Thanh toán qua PayOS/gi, "Thanh toán trực tuyến")
    .replace(/PayOS/gi, "đơn vị thanh toán");
  const normalizedBody = customerFacingBody.replace(
    /<a\b([^>]*\bhref\s*=\s*(["'])\/admin\/payments(?:\?[^"']*)?\2[^>]*)>[\s\S]*?<\/a>/gi,
    (_match, attributes: string) => `<a${attributes}>Thu phí</a>`,
  );
  const html = normalizedBody.replace(
    /<h([23])\b([^>]*)>([\s\S]*?)<\/h\1>/gi,
    (_match, rawLevel: string, rawAttributes: string, contents: string) => {
      const text = decodeGuideHtmlText(contents.replace(/<[^>]*>/g, " "))
        .replace(/\s+/g, " ")
        .trim();
      const base = toGuideHeadingId(text);
      const occurrence = (occurrences.get(base) ?? 0) + 1;
      occurrences.set(base, occurrence);
      const id = toGuideHeadingId(text, occurrence);
      headings.push({ id, text, level: Number(rawLevel) as 2 | 3 });
      const attributes = rawAttributes.replace(
        /\s+id\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi,
        "",
      );
      return `<h${rawLevel}${attributes} id="${id}">${contents}</h${rawLevel}>`;
    },
  );
  return { html, headings };
}

export function decodeGuideHtmlText(value: string): string {
  const named: Record<string, string> = {
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    nbsp: " ",
    quot: '"',
  };
  return value.replace(
    /&(#(?:x[\da-f]+|\d+)|[a-z]+);/gi,
    (entity, value: string) => {
      if (value.startsWith("#x") || value.startsWith("#X")) {
        const codePoint = Number.parseInt(value.slice(2), 16);
        return isValidCodePoint(codePoint)
          ? String.fromCodePoint(codePoint)
          : entity;
      }
      if (value.startsWith("#")) {
        const codePoint = Number.parseInt(value.slice(1), 10);
        return isValidCodePoint(codePoint)
          ? String.fromCodePoint(codePoint)
          : entity;
      }
      return named[value.toLowerCase()] ?? entity;
    },
  );
}

function htmlToPlainText(value: string): string {
  return decodeGuideHtmlText(value.replace(/<[^>]*>/g, " "))
    .replace(/\s+/g, " ")
    .trim();
}

function isValidCodePoint(value: number): boolean {
  return (
    Number.isInteger(value) &&
    value >= 0 &&
    value <= 0x10ffff &&
    (value < 0xd800 || value > 0xdfff)
  );
}
