import { PublicMap } from "@/components/public/public-map";

export default async function MapPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category } = await searchParams;
  return (
    <div className="mx-auto min-h-[calc(100dvh-5rem)] max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
        Bản đồ tài sản
      </p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-6xl">
        Dấu ấn giá trị trên lãnh thổ.
      </h1>
      <p className="mt-4 max-w-2xl text-slate-400">
        Khám phá các tài sản công khai có dữ liệu tọa độ đã được xác lập.
      </p>
      <div className="mt-10">
        <PublicMap category={category} />
      </div>
    </div>
  );
}
