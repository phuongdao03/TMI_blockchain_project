"use client";

import { ArrowLeft, ArrowRight, Maximize2, X } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

const categories = [
  "Tất cả",
  "Nghi thức & sự kiện",
  "Kết nối & thực địa",
  "Văn hóa & đời sống",
] as const;

const photos = (
  [
    ["01", "Lễ công bố và trao quyết định xác lập"],
    ["35", "Trao quyết định trên sân khấu"],
    ["04", "Phát biểu tại lễ công bố"],
    ["07", "Khoảnh khắc lưu niệm trên sân khấu"],
    ["21", "Những tiết mục trong chương trình"],
    ["34", "Dấu ấn lễ công bố Tinh Hoa Việt"],
    ["10", "Nghi thức trao Bằng Xác lập"],
    ["12", "Ghi nhận và tôn vinh giá trị"],
    ["23", "Chia sẻ tại lễ công bố và xác lập"],
    ["36", "Tôn vinh những giá trị được ghi nhận"],
    ["28", "Bằng Xác lập trong không gian trưng bày"],
    ["31", "Kết nối với cộng đồng học đường"],
    ["30", "Khoảnh khắc lưu niệm cùng đơn vị"],
    ["14", "Cùng học sinh khám phá không gian văn hóa"],
    ["08", "Văn phòng đại diện tại TP. Đồng Nai"],
    ["05", "Gặp gỡ và kết nối mạng lưới đồng hành"],
    ["03", "Trao đổi, làm việc cùng các đơn vị"],
    ["15", "Làm việc và trao đổi chuyên môn"],
    ["24", "Kết nối để cùng phát huy giá trị"],
    ["29", "Trao đổi nội dung và phối hợp triển khai"],
    ["38", "Làm việc cùng các đối tác"],
    ["11", "Tìm hiểu những hiện vật văn hóa"],
    ["16", "Khám phá không gian trưng bày di sản"],
    ["17", "Tiếp cận và tìm hiểu hiện vật"],
    ["26", "Khảo sát các sản phẩm thủ công"],
    ["27", "Gặp gỡ người lưu giữ hiện vật"],
    ["18", "Trao đổi về các giá trị tại địa phương"],
    ["19", "Gặp gỡ các đơn vị tại địa phương"],
    ["25", "Tìm hiểu một không gian trưng bày địa phương"],
    ["20", "Khảo sát mô hình trồng trọt"],
    ["02", "Sắc màu nghề đan truyền thống"],
    ["13", "Nét kiến trúc phố cổ bên dòng sông"],
    ["09", "Đời sống trên miền sông nước"],
    ["06", "Hương vị ẩm thực đường phố"],
    ["22", "Sự phong phú của ẩm thực"],
    ["33", "Câu chuyện từ những món ăn"],
    ["32", "Con người và cảnh sắc vùng cao"],
    ["37", "Nét đẹp trong đời sống thường ngày"],
  ] as const
).map(([id, title], position) => ({
  file: `gallery-${id}-large.webp`,
  title,
  category:
    position < 13
      ? categories[1]
      : position < 30
        ? categories[2]
        : categories[3],
}));

export function HeritageGallery() {
  const [category, setCategory] =
    useState<(typeof categories)[number]>("Tất cả");
  const [index, setIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const expandButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const visible =
    category === "Tất cả"
      ? photos
      : photos.filter((photo) => photo.category === category);
  const photo = visible[index] ?? visible[0]!;
  const largePhoto = `/assets/institution/${photo.file}`;

  useEffect(() => {
    if (!expanded) return;
    const expandButton = expandButtonRef.current;
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
      if (event.key === "Tab") {
        event.preventDefault();
        closeButtonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      expandButton?.focus();
    };
  }, [expanded]);

  function move(direction: number) {
    setIndex(
      (current) => (current + direction + visible.length) % visible.length,
    );
  }

  return (
    <section
      aria-labelledby="heritage-gallery-title"
      className="institution-section institution-section--gallery"
      id="thu-vien-anh"
    >
      <div className="institution-section__inner">
        <div className="institution-section__heading">
          <div>
            <p className="institution-eyebrow">Thư viện hình ảnh</p>
            <h2 id="heritage-gallery-title">
              Những khoảnh khắc. <span>Những giá trị lưu truyền.</span>
            </h2>
          </div>
          <p className="institution-section__summary">
            Hình ảnh nghi thức công bố, hoạt động kết nối cùng những sắc màu văn
            hóa và đời sống trong bộ sưu tập Tinh Hoa Việt.
          </p>
        </div>
        <div aria-label="Lọc bộ sưu tập" className="heritage-gallery__filters">
          {categories.map((item) => (
            <button
              aria-pressed={item === category}
              key={item}
              onClick={() => {
                setCategory(item);
                setIndex(0);
              }}
              type="button"
            >
              {item}{" "}
              <span>
                {item === "Tất cả"
                  ? photos.length
                  : photos.filter((photo) => photo.category === item).length}
              </span>
            </button>
          ))}
        </div>
        <div className="heritage-gallery">
          <div className="heritage-gallery__stage">
            <Image
              alt={photo.title}
              fill
              key={photo.file}
              sizes="(max-width: 48rem) 100vw, (max-width: 80rem) 90vw, 1280px"
              src={largePhoto}
            />
            <span className="heritage-gallery__counter">
              {String(index + 1).padStart(2, "0")} /{" "}
              {String(visible.length).padStart(2, "0")}
            </span>
            <button
              aria-label="Xem toàn màn hình"
              className="heritage-gallery__expand"
              onClick={() => setExpanded(true)}
              ref={expandButtonRef}
              type="button"
            >
              <Maximize2 aria-hidden="true" size={17} />{" "}
              <span>Xem toàn màn hình</span>
            </button>
          </div>
          <div className="heritage-gallery__bottom">
            <div>
              <small>{photo.category}</small>
              <h3>{photo.title}</h3>
            </div>
            <div className="heritage-gallery__arrows">
              <button
                aria-label="Ảnh trước"
                onClick={() => move(-1)}
                type="button"
              >
                <ArrowLeft aria-hidden="true" size={19} />
              </button>
              <button
                aria-label="Ảnh tiếp theo"
                onClick={() => move(1)}
                type="button"
              >
                <ArrowRight aria-hidden="true" size={19} />
              </button>
            </div>
          </div>
        </div>
        <div
          aria-label="Chọn ảnh trong bộ sưu tập"
          className="heritage-gallery__thumbnails"
        >
          {visible.map((item, position) => (
            <button
              aria-current={position === index ? "true" : undefined}
              aria-label={`Xem ảnh ${position + 1}: ${item.title}`}
              key={item.file}
              onClick={() => setIndex(position)}
              type="button"
            >
              <Image
                alt=""
                height={90}
                sizes="104px"
                src={`/assets/institution/${item.file}`}
                width={160}
              />
            </button>
          ))}
        </div>
      </div>
      {expanded ? (
        <div
          aria-label="Ảnh Tinh Hoa Việt"
          aria-modal="true"
          className="heritage-gallery__modal"
          role="dialog"
        >
          <button
            aria-label="Đóng ảnh toàn màn hình"
            className="heritage-gallery__close"
            onClick={() => setExpanded(false)}
            ref={closeButtonRef}
            type="button"
          >
            <X aria-hidden="true" size={24} />
          </button>
          <div className="heritage-gallery__modal-image">
            <Image alt={photo.title} fill sizes="100vw" src={largePhoto} />
          </div>
          <p>{photo.title}</p>
        </div>
      ) : null}
    </section>
  );
}
