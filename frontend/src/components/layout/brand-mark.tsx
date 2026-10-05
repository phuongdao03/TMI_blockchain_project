import Image from "next/image";
import Link from "next/link";

type BrandMarkProps = {
  compact?: boolean;
  showCredit?: boolean;
  variant?: "default" | "public-seal";
};

export function BrandMark({
  compact = false,
  showCredit = false,
  variant = "default",
}: BrandMarkProps) {
  const sealOnly = variant === "public-seal";
  return (
    <Link
      aria-label="Đề cử và xác lập Tinh Hoa Việt"
      className={`brand-mark brand-mark--official${compact ? " brand-mark--compact" : ""}${sealOnly ? " brand-mark--public-seal" : ""}`}
      href="/"
      prefetch={false}
    >
      <Image
        alt=""
        aria-hidden="true"
        className="brand-mark__official-logo"
        height={256}
        priority
        src="/assets/brand/logo-tinh-hoa-viet.png"
        width={256}
      />
      {!sealOnly ? (
        <span className="brand-mark__official-name" aria-hidden="true">
          <span>Đề cử và xác lập</span>
          <strong>Tinh Hoa Việt</strong>
        </span>
      ) : null}
      {showCredit ? (
        <span className="brand-mark__credit">Nền tảng Đề cử Tinh Hoa Việt</span>
      ) : null}
    </Link>
  );
}
