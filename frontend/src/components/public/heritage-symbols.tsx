import Image from "next/image";

export function HeritageSymbols() {
  return (
    <div className="registry-heritage" id="dau-an-van-hoa">
      <figure className="registry-heritage__logo">
        <Image
          alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
          fetchPriority="high"
          height={2048}
          loading="eager"
          sizes="(max-width: 48rem) 76vw, 38vw"
          src="/assets/brand/logo-tinh-hoa-viet.png"
          width={2048}
        />
      </figure>
    </div>
  );
}
