import Image from "next/image";

export function HeritageSymbols() {
  return (
    <figure className="registry-heritage" id="dau-an-van-hoa">
      <Image
        alt=""
        aria-hidden="true"
        className="registry-heritage__drum"
        height={512}
        loading="eager"
        sizes="(max-width: 48rem) 280px, 560px"
        src="/assets/brand/trong-dong.png"
        width={512}
      />
      <Image
        alt=""
        aria-hidden="true"
        className="registry-heritage__bird"
        height={512}
        sizes="(max-width: 48rem) 100px, 160px"
        src="/assets/brand/chim-lac.jpg"
        width={512}
      />
      <span className="registry-heritage__seal">
        <Image
          alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
          className="registry-heritage__logo"
          height={512}
          loading="eager"
          sizes="(max-width: 48rem) 260px, 360px"
          src="/assets/brand/logo-tinh-hoa-viet.png"
          width={512}
        />
        <span aria-hidden="true" className="registry-heritage__light" />
        <span aria-hidden="true" className="registry-heritage__glint" />
      </span>
      <figcaption className="sr-only">
        Chim Lạc, trống đồng và biểu trưng Tinh Hoa Việt.
      </figcaption>
    </figure>
  );
}
