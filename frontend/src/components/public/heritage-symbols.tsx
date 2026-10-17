import Image from "next/image";

export function HeritageSymbols() {
  return (
    <figure className="registry-heritage" id="dau-an-van-hoa">
      <Image
        alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
        className="registry-heritage__logo"
        height={512}
        loading="eager"
        sizes="(max-width: 48rem) 280px, 440px"
        src="/assets/brand/logo-tinh-hoa-viet.png"
        width={512}
      />
    </figure>
  );
}
