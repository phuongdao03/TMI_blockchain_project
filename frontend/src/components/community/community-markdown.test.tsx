import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CommunityMarkdown } from "@/components/community/community-markdown";

describe("CommunityMarkdown", () => {
  it("renders headings, emphasis, lists, quotes, paragraphs and safe links", () => {
    render(
      <CommunityMarkdown
        content={[
          "## Câu chuyện",
          "",
          "Một **điều hay** và *một điều khác*.",
          "",
          "- Làng nghề",
          "- Di sản",
          "",
          "1. Ghi chép",
          "2. Chia sẻ",
          "",
          "> Một lời nhắn",
          "",
          "[Đọc thêm](/works/gom-lang-co)",
        ].join("\n")}
      />,
    );

    expect(screen.getByRole("heading", { name: "Câu chuyện" })).toBeDefined();
    expect(screen.getByText("điều hay").tagName).toBe("STRONG");
    expect(screen.getByText("một điều khác").tagName).toBe("EM");
    expect(
      screen.getByRole("list", { name: "Danh sách không thứ tự" }),
    ).toBeDefined();
    expect(
      screen.getByRole("list", { name: "Danh sách có thứ tự" }),
    ).toBeDefined();
    expect(screen.getByRole("blockquote")).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Đọc thêm" }).getAttribute("href"),
    ).toBe("/works/gom-lang-co");
  });

  it("renders raw HTML and unsafe URL syntax as text without creating elements or links", () => {
    render(
      <CommunityMarkdown
        content={
          "<img src=x onerror=alert(1)>\n\n[javascript](javascript:alert(1))"
        }
      />,
    );

    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeDefined();
    expect(screen.queryByRole("link", { name: "javascript" })).toBeNull();
    expect(screen.getByText("javascript)")).toBeDefined();
  });

  it("does not allow protocol-relative or backslash links", () => {
    render(
      <CommunityMarkdown
        content={"[ngoài](//evil.test)\n\n[ngoài nữa](/\\evil.test)"}
      />,
    );

    expect(screen.queryByRole("link", { name: "ngoài" })).toBeNull();
    expect(screen.queryByRole("link", { name: "ngoài nữa" })).toBeNull();
  });
});
