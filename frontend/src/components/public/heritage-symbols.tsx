import Image from "next/image";

export function HeritageSymbols() {
  return (
    <figure className="registry-heritage" id="dau-an-van-hoa">
      <span className="registry-heritage__seal">
        <Image
          alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
          className="registry-heritage__logo"
          height={512}
          loading="eager"
          sizes="(max-width: 48rem) 280px, 440px"
          src="/assets/brand/logo-tinh-hoa-viet.png"
          width={512}
        />
        <span aria-hidden="true" className="registry-heritage__glint" />
      </span>
    </figure>
  );
}
