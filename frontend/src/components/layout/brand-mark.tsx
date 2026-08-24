import Image from "next/image";
import Link from "next/link";

type BrandMarkProps = {
  compact?: boolean;
  showCredit?: boolean;
};

export function BrandMark({
  compact = false,
  showCredit = false,
}: BrandMarkProps) {
  return (
    <Link
      aria-label="Trung tâm Đề cử Tinh Hoa Việt"
      className={`brand-mark${compact ? " brand-mark--compact" : ""}`}
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
