import Image from "next/image";

export function HeritageSymbols() {
  return (
    <div className="registry-heritage" id="dau-an-van-hoa">
      <figure className="registry-heritage__logo">
        <Image
          alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
          height={2048}
          loading="lazy"
          sizes="(max-width: 48rem) 88px, 38vw"
          src="/assets/brand/logo-tinh-hoa-viet.png"
          width={2048}
        />
      </figure>
    </div>
  );
}
