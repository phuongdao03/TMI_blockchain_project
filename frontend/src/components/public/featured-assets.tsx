"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PublicWorkCard } from "@/components/public/public-work-card";
import { publicApi } from "@/lib/api/client";

export function FeaturedAssets() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [nearViewport, setNearViewport] = useState(false);

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
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
      { rootMargin: "400px" },
    );
    observer.observe(section);
    return () => observer.disconnect();
  }, []);

  const query = useQuery({
    queryKey: ["public-featured-assets"],
    queryFn: () => publicApi.works({ page: 1, pageSize: 3 }),
    staleTime: 30_000,
    enabled: nearViewport,
  });
  if (query.isPending) {
    return (
      <div className="grid gap-4 md:grid-cols-3" ref={sectionRef} role="status">
        <span className="sr-only">Đang tải đề cử đã công bố…</span>
        {[0, 1, 2].map((item) => (
          <div
            aria-hidden="true"
            className="dashboard-skeleton h-48 animate-pulse rounded-xl"
            key={item}
          />
        ))}
      </div>
    );
  }
  if (query.isError) {
    return (
      <div
        className="grid min-h-52 place-items-center border-y border-dashed border-neutral-300 px-6 py-10 text-center"
        ref={sectionRef}
      >
        <div>
          <CircleAlert
            aria-hidden="true"
            className="mx-auto size-6 text-primary-700"
          />
          <p className="mt-3 font-bold">Chưa thể tải đề cử</p>
          <p className="mt-1 text-sm text-neutral-600">
            Vui lòng kiểm tra kết nối và thử lại.
          </p>
          <button
            className="mt-4 min-h-11 rounded-lg border border-neutral-300 px-4 text-sm font-bold"
            onClick={() => void query.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }
  if (!query.data?.data.length) {
    return (
      <div
        className="border-y border-dashed border-neutral-300 px-6 py-12 text-center text-sm text-neutral-600"
        ref={sectionRef}
      >
        Tài sản tiêu biểu sẽ xuất hiện sau khi được công bố.
      </div>
    );
  }
  const featured = query.data.data;
  return (
    <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3" ref={sectionRef}>
      {featured.map((work, index) => (
        <PublicWorkCard
          key={work.id}
          position={index + 1}
          source="list"
          work={work}
        />
      ))}
    </div>
  );
}
