import { describe, expect, it } from "vitest";

import {
  getGuideFaqItems,
  prepareGuideArticleBody,
} from "@/components/guide/guide-content";

describe("guide article content", () => {
  it("builds a linked contents list from heading markup", () => {
    const result = prepareGuideArticleBody(
      "<h2>Tạo hồ sơ</h2><p>Điền thông tin.</p><h3>Tạo hồ sơ</h3>",
    );

    expect(result.headings).toEqual([
      { id: "tao-ho-so", text: "Tạo hồ sơ", level: 2 },
      { id: "tao-ho-so-2", text: "Tạo hồ sơ", level: 3 },
    ]);
    expect(result.html).toContain('<h2 id="tao-ho-so">');
    expect(result.html).toContain('<h3 id="tao-ho-so-2">');
    expect(result.html).toContain("<p>Điền thông tin.</p>");
  });

  it("decodes text entities for readable contents labels", () => {
    const result = prepareGuideArticleBody("<h2>Thông tin &amp; xác minh</h2>");
    expect(result.headings[0]?.text).toBe("Thông tin & xác minh");
  });

  it("extracts FAQ entries only from the FAQ section", () => {
    expect(
      getGuideFaqItems(
        "<h2>Trước khi bắt đầu</h2><p>Điều kiện.</p>" +
          "<h2>Câu hỏi thường gặp</h2><h3>Tôi bắt đầu từ đâu?</h3>" +
          '<p>Mở <a href="/works">thư viện</a> &amp; chọn đề mục.</p>' +
          "<h3>Khi nào?</h3><p>Sau khi đăng nhập.</p><h2>Lưu ý</h2>",
      ),
    ).toEqual([
      {
        question: "Tôi bắt đầu từ đâu?",
        answer: "Mở thư viện & chọn đề mục.",
      },
      { question: "Khi nào?", answer: "Sau khi đăng nhập." },
    ]);
  });
});
