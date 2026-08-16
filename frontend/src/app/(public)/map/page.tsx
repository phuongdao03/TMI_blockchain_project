import { PublicMap } from "@/components/public/public-map";
import { getServerAuthState } from "@/lib/auth/server-session";

export default async function MapPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category } = await searchParams;
  const { user } = await getServerAuthState();
  const embedded = Boolean(user);
  return (
    <div
      className={
        embedded
          ? "mx-auto max-w-7xl rounded-2xl bg-[#151515] px-5 py-7 text-white shadow-[0_24px_70px_rgba(15,23,42,.12)] sm:px-7 lg:px-9"
          : "mx-auto min-h-[calc(100dvh-5rem)] max-w-7xl px-4 py-14 sm:px-6 lg:px-8"
      }
    >
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
        Bản đồ đề cử
      </p>
      <h1
        className={`mt-4 font-bold tracking-tight ${
          embedded ? "text-3xl sm:text-4xl" : "text-4xl sm:text-6xl"
        }`}
      >
        Khám phá đề cử theo khu vực
      </h1>
      <p className="mt-4 max-w-2xl text-slate-400">
        Xem các nội dung đã công bố theo địa điểm và khu vực.
      </p>
      <div className="mt-10 overflow-hidden rounded-2xl bg-[#151515] p-3 text-white shadow-[0_24px_70px_rgba(15,23,42,.1)] sm:p-5">
        <PublicMap category={category} />
      </div>
    </div>
  );
}
