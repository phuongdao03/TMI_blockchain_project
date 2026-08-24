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
  const usesPublicSeal = !compact && variant === "public-seal";

  return (
    <Link
      aria-label="Trung tâm Đề cử Tinh Hoa Việt"
      className={`brand-mark${compact ? " brand-mark--compact" : ""}${usesPublicSeal ? " brand-mark--public-seal" : ""}`}
      href="/"
    >
      {compact ? (
        <Image
          className="brand-mark__emblem"
          src="/assets/brand/thv-brand-emblem.png"
          alt=""
          width={1254}
          height={1254}
          priority
        />
      ) : usesPublicSeal ? (
        <span className="brand-mark__public-lockup" aria-hidden="true">
          <span className="brand-mark__seal-frame">
            <Image
              className="brand-mark__seal"
              src="/assets/brand/thv-public-header-seal.png"
              alt=""
              width={1253}
              height={1254}
              priority
            />
          </span>
          <span className="brand-mark__public-wordmark-frame">
            <Image
              className="brand-mark__public-wordmark"
              src="/assets/brand/thv-public-header-wordmark.png"
              alt=""
              width={1448}
              height={1086}
              priority
            />
          </span>
        </span>
      ) : (
        <span className="brand-mark__wordmark-frame" aria-hidden="true">
          <Image
            className="brand-mark__wordmark"
            src="/assets/brand/thv-brand-wordmark.png"
            alt=""
            width={1448}
            height={1086}
            priority
          />
        </span>
      )}
      {showCredit ? (
        <span className="brand-mark__credit">
          Phát triển bởi Trung tâm An ninh Công nghệ số – CNS
        </span>
      ) : null}
    </Link>
  );
}
