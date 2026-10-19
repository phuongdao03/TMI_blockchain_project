import { expect, type Page } from "@playwright/test";

export async function expectDocumentToFit(
  page: Page,
  message: string,
  tolerance = 0,
) {
  try {
    await expect
      .poll(
        () =>
          page.evaluate(
            (allowedOverflow) =>
              document.documentElement.scrollWidth <=
              window.innerWidth + allowedOverflow,
            tolerance,
          ),
        { message, timeout: 15_000 },
      )
      .toBe(true);
  } catch {
    const diagnostic = await page.evaluate(() => {
      const viewport = window.innerWidth;
      const candidates = [
        document.body,
        ...Array.from(document.body.querySelectorAll("*")),
      ]
        .map((element) => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          let clippedByAncestor = false;
          for (
            let ancestor = element.parentElement;
            ancestor;
            ancestor = ancestor.parentElement
          ) {
            if (
              ["auto", "scroll", "hidden", "clip"].includes(
                getComputedStyle(ancestor).overflowX,
              )
            ) {
              clippedByAncestor = true;
              break;
            }
          }
          return {
            tag: element.tagName.toLowerCase(),
            id: element.id,
            className:
              typeof element.className === "string"
                ? element.className.slice(0, 120)
                : "",
            text: element.textContent?.replace(/\s+/g, " ").slice(0, 70),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            scrollWidth: element.scrollWidth,
            clientWidth: element.clientWidth,
            overflowX: style.overflowX,
            clippedByAncestor,
          };
        })
        .filter(
          (element) =>
            element.width > 0 &&
            !element.clippedByAncestor &&
            (element.right > viewport + 1 || element.left < -1),
        )
        .sort(
          (a, b) =>
            Math.max(b.right - viewport, -b.left) -
            Math.max(a.right - viewport, -a.left),
        )
        .slice(0, 12);

      return {
        viewport,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
        candidates,
      };
    });

    throw new Error(`${message}: ${JSON.stringify(diagnostic)}`);
  }
}
