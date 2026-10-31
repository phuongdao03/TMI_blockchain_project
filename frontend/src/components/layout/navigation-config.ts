import {
  BadgeCheck,
  BookOpen,
  CircleHelp,
  Download,
  FilePlus2,
  Gem,
  House,
  Mail,
  Route,
  ScrollText,
  UsersRound,
} from "lucide-react";

export const navigationGroups = [
  {
    label: "Khám phá",
    items: [
      { href: "/", label: "Trang chủ", icon: House },
      { href: "/works", label: "Khám phá đề cử", icon: BookOpen },
      { href: "/community", label: "Cộng đồng", icon: UsersRound },
      { href: "/verify", label: "Tra cứu bằng xác lập", icon: BadgeCheck },
    ],
  },
  {
    label: "Tham gia",
    items: [
      { href: "/dossiers/new", label: "Gửi hồ sơ đề cử", icon: FilePlus2 },
      { href: "/process", label: "Quy trình đề cử", icon: Route },
      { href: "/cong-dong/hoi-vien", label: "Cộng đồng hội viên", icon: Gem },
    ],
  },
  {
    label: "Hỗ trợ",
    items: [
      { href: "/guide", label: "Hướng dẫn", icon: CircleHelp },
      { href: "/#lien-he", label: "Liên hệ", icon: Mail },
      { href: "/policies", label: "Điều khoản sử dụng", icon: ScrollText },
      { href: "/policies#privacy", label: "Quyền riêng tư", icon: BadgeCheck },
      { href: "/install", label: "Cài ứng dụng", icon: Download },
    ],
  },
];

export function matchesNavigation(pathname: string, href: string, hash = "") {
  const [path, anchor] = href.split("#");
  if (anchor) return pathname === path && hash === `#${anchor}`;
  if (href === "/") return pathname === "/" && !hash;
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function activeNavigationHref(
  pathname: string,
  hrefs: string[],
  hash = "",
) {
  return hrefs
    .filter((href) => matchesNavigation(pathname, href, hash))
    .sort((a, b) => b.length - a.length)[0];
}
