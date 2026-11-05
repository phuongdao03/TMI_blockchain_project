import { describe, expect, it } from "vitest";

import {
  getGuideFaqItems,
  prepareGuideArticleBody,
} from "@/components/guide/guide-content";
import { getStarterGuide } from "@/components/guide/guide-fallback-content";

describe("guide article content", () => {
  it("keeps the built-in top-up instructions focused on payment requirements", () => {
    const guide = getStarterGuide("huong-dan-nap-tien-vao-vi");

    expect(guide?.bodyHtml).toContain(
      "<li>Nhập số tiền muốn nạp, tối thiểu 5.000đ.</li>",
    );
    expect(guide?.bodyHtml).not.toMatch(/dấu chấm|hiển thị tự động/i);
    expect(guide?.bodyHtml).toContain("10 phút");
    expect(guide?.bodyHtml).toContain("giữ nguyên nội dung chuyển khoản");
    expect(guide?.bodyHtml).toContain("đừng thanh toán lần nữa");
  });

  it.each([
    "Nhập số tiền cần nạp. Mức tối thiểu là 5.000 đồng; dấu chấm phân cách hàng nghìn được hiển thị tự động.",
    "Nhập số tiền muốn nạp, tối thiểu 5.000đ. Dấu chấm phân cách hàng nghìn sẽ hiển thị tự động.",
  ])("edits obsolete top-up guidance received from the CMS: %s", (step) => {
    const result = prepareGuideArticleBody(
      `<ol><li>${step}</li></ol><p>Yêu cầu có hiệu lực trong 10 phút. Giữ nguyên nội dung chuyển khoản.</p>`,
    );

    expect(result.html).toContain(
      "<li>Nhập số tiền muốn nạp, tối thiểu 5.000đ.</li>",
    );
    expect(result.html).not.toMatch(/dấu chấm|hiển thị tự động/i);
    expect(result.html).toContain(
      "Yêu cầu có hiệu lực trong 10 phút. Giữ nguyên nội dung chuyển khoản.",
    );
  });

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
