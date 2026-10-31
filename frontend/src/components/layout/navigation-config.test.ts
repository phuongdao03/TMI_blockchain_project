import { describe, expect, it } from "vitest";
import {
  activeNavigationHref,
  matchesNavigation,
  navigationGroups,
} from "./navigation-config";

describe("navigation destinations", () => {
  it("selects only the most specific parent and honors path boundaries", () => {
    expect(
      activeNavigationHref("/dossiers/new", ["/dossiers", "/dossiers/new"]),
    ).toBe("/dossiers/new");
    expect(matchesNavigation("/workshop", "/works")).toBe(false);
    expect(matchesNavigation("/works/example", "/works")).toBe(true);
  });
  it("matches homepage anchors without activating every homepage link", () => {
    expect(
      activeNavigationHref(
        "/",
        ["/", "/#thu-vien-anh", "/#gioi-thieu"],
        "#thu-vien-anh",
      ),
    ).toBe("/#thu-vien-anh");
    expect(matchesNavigation("/", "/#gioi-thieu", "#thu-vien-anh")).toBe(false);
  });
  it("omits the redundant About section from navigation", () => {
    expect(
      navigationGroups.some((group) => group.label === "Về Tinh Hoa Việt"),
    ).toBe(false);
  });
});
