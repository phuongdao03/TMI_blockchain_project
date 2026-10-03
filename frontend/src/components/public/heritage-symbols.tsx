import Image from "next/image";

export function HeritageSymbols() {
  return (
    <div className="registry-heritage" id="dau-an-van-hoa">
      <span aria-hidden="true" className="registry-heritage__outline" />
      <figure className="registry-heritage__bird">
        <Image
          alt="Họa tiết chim Lạc màu trắng trên nền đỏ"
          height={2048}
          loading="eager"
          sizes="(max-width: 48rem) 28vw, 16vw"
          src="/assets/brand/chim-lac.jpg"
          width={2048}
        />
      </figure>
      <figure className="registry-heritage__drum">
        <Image
          alt="Họa tiết mặt trống đồng với các vòng hoa văn đồng tâm"
          height={2048}
          loading="eager"
          sizes="(max-width: 48rem) 30vw, 17vw"
          src="/assets/brand/trong-dong.png"
          width={2048}
        />
      </figure>
      <figure className="registry-heritage__logo">
        <Image
          alt="Biểu trưng Trung tâm Xác lập Tinh Hoa Việt"
          fetchPriority="high"
          height={2048}
          loading="eager"
          sizes="(max-width: 48rem) 67vw, 34vw"
          src="/assets/brand/logo-tinh-hoa-viet.png"
          width={2048}
        />
      </figure>
    </div>
  );
}
