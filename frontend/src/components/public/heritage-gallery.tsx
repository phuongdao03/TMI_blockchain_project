"use client";

import { ArrowLeft, ArrowRight, Maximize2 } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { ImageLoadingStatus } from "@/components/media/image-loading-status";

import { HeritageLightbox } from "./heritage-lightbox";

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
  const [loadedFile, setLoadedFile] = useState<string>();
  const [failedFile, setFailedFile] = useState<string>();
  const [retry, setRetry] = useState(0);
  const [nearViewport, setNearViewport] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const visible =
    category === "Tất cả"
      ? photos
      : photos.filter((photo) => photo.category === category);
  const photo = visible[index] ?? visible[0]!;
  const thumbnails = visible
    .filter((_, position) => position % Math.ceil(visible.length / 6) === 0)
    .slice(0, 6);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    if (!("IntersectionObserver" in window)) {
      queueMicrotask(() => setNearViewport(true));
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setNearViewport(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!nearViewport || loadedFile === photo.file || failedFile === photo.file)
      return;
    const timeout = window.setTimeout(() => setFailedFile(photo.file), 15_000);
    return () => window.clearTimeout(timeout);
  }, [nearViewport, loadedFile, failedFile, photo.file, retry]);

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
        <div className="heritage-gallery">
          <div className="heritage-gallery__stage" ref={stageRef}>
            <button
              className="heritage-gallery__open-image"
              aria-label={`Xem ảnh: ${photo.title}`}
              onClick={() => setExpanded(true)}
              type="button"
            >
              <Image
                alt={photo.title}
                fill
                key={`${photo.file}-${retry}`}
                onError={() => setFailedFile(photo.file)}
                onLoad={() => setLoadedFile(photo.file)}
                sizes="(max-width: 48rem) 100vw, 1280px"
                src={`/assets/institution/${photo.file}`}
              />
            </button>
            {nearViewport &&
              loadedFile !== photo.file &&
              failedFile !== photo.file && <ImageLoadingStatus />}
            {failedFile === photo.file && (
              <div className="heritage-gallery__error" role="alert">
                <p>Chưa thể tải ảnh này.</p>
                <button
                  type="button"
                  onClick={() => {
                    setFailedFile(undefined);
                    setRetry((value) => value + 1);
                  }}
                >
                  Thử tải lại ảnh
                </button>
              </div>
            )}
            <span className="heritage-gallery__counter">
              {String(index + 1).padStart(2, "0")} /{" "}
              {String(visible.length).padStart(2, "0")}
            </span>
            <button
              aria-label="Xem toàn màn hình"
              className="heritage-gallery__expand"
              onClick={() => setExpanded(true)}
              type="button"
            >
              <Maximize2 aria-hidden="true" size={18} />
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
                <ArrowLeft aria-hidden="true" size={20} />
              </button>
              <button
                aria-label="Ảnh tiếp theo"
                onClick={() => move(1)}
                type="button"
              >
                <ArrowRight aria-hidden="true" size={20} />
              </button>
            </div>
          </div>
        </div>
        <label className="heritage-gallery__mobile-filter">
          <span>Chọn bộ ảnh</span>
          <select
            value={category}
            onChange={(event) => {
              const selected = categories.find(
                (item) => item === event.target.value,
              );
              if (selected) {
                setCategory(selected);
                setIndex(0);
              }
            }}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item} ·{" "}
                {item === "Tất cả"
                  ? photos.length
                  : photos.filter((photo) => photo.category === item)
                      .length}{" "}
                ảnh
              </option>
            ))}
          </select>
        </label>
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
        <div
          aria-label="Chọn ảnh trong bộ sưu tập"
          className="heritage-gallery__thumbnails"
          role="group"
        >
          {nearViewport
            ? thumbnails.map((item) => (
                <button
                  aria-current={
                    visible.indexOf(item) === index ? "true" : undefined
                  }
                  aria-label={`Xem ảnh ${visible.indexOf(item) + 1}: ${item.title}`}
                  key={item.file}
                  onClick={() => setIndex(visible.indexOf(item))}
                  type="button"
                >
                  <Image
                    alt=""
                    height={160}
                    sizes="(max-width: 48rem) 45vw, 200px"
                    src={`/assets/institution/${item.file}`}
                    width={240}
                  />
                </button>
              ))
            : null}
        </div>
        <button
          className="heritage-gallery__explore institution-button"
          type="button"
          onClick={() => setExpanded(true)}
        >
          Khám phá tất cả hình ảnh <span>{visible.length} ảnh</span>
        </button>
      </div>
      {expanded && (
        <HeritageLightbox
          photo={photo}
          index={index}
          total={visible.length}
          onMove={move}
          onClose={() => setExpanded(false)}
        />
      )}
    </section>
  );
}
