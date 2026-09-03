import { Check, RotateCcw } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { DateControl, SelectControl } from "@/components/ui/form-controls";
import { searchHref } from "@/components/search/search-url";
import type { SearchFacets, SearchParameters } from "@/lib/api/types";

const controlClass =
  "mt-2 min-h-11 w-full rounded-lg border border-white/10 bg-ink-950 px-3 text-sm text-white outline-none transition focus:border-gold-300 focus:ring-2 focus:ring-gold-300/20";

export function SearchFilters({
  facets,
  layout = "sidebar",
  parameters,
}: {
  facets?: SearchFacets;
  layout?: "sidebar" | "panel";
  parameters: SearchParameters;
}) {
  const panel = layout === "panel";
  return (
    <div
      className={
        panel
          ? "grid gap-6 xl:grid-cols-[minmax(0,.8fr)_minmax(0,.8fr)_minmax(22rem,1.4fr)]"
          : "space-y-7"
      }
    >
      <FacetGroup label="Danh mục">
        <FacetLink
          active={!parameters.category}
          href={searchHref({
            ...parameters,
            category: undefined,
            cursor: undefined,
          })}
          label="Tất cả danh mục"
        />
        {facets?.categories.map((item) => (
          <FacetLink
            active={parameters.category === item.slug}
            count={item.count}
            href={searchHref({
              ...parameters,
              category: item.slug,
              cursor: undefined,
            })}
            key={item.slug}
            label={item.label}
          />
        ))}
      </FacetGroup>

      <FacetGroup label="Chủ đề">
        {facets?.tags.map((item) => {
          const active = parameters.tags.includes(item.slug);
          const tags = active
            ? parameters.tags.filter((slug) => slug !== item.slug)
            : [...parameters.tags, item.slug];
          return (
            <FacetLink
              active={active}
              count={item.count}
              href={searchHref({ ...parameters, tags, cursor: undefined })}
              key={item.slug}
              label={item.label}
            />
          );
        })}
        {!facets?.tags.length ? (
          <p className="text-sm leading-6 text-slate-500">
            Chưa có chủ đề trong tập kết quả này.
          </p>
        ) : null}
      </FacetGroup>

      <form
        action="/search"
        className={panel ? "grid gap-4 sm:grid-cols-2" : "space-y-4"}
        method="get"
      >
        <HiddenSearchState parameters={parameters} />
        <label className="block text-sm font-semibold text-slate-300">
          Cách khớp chủ đề
          <SelectControl
            className={controlClass}
            defaultValue={parameters.tagsMode}
            name="tagsMode"
          >
            <option value="any">Khớp một chủ đề</option>
            <option value="all">Khớp tất cả chủ đề</option>
          </SelectControl>
        </label>
        <label className="block text-sm font-semibold text-slate-300">
          Tổ chức
          <input
            className={controlClass}
            defaultValue={parameters.organization}
            maxLength={160}
            name="organization"
            placeholder="Mã tổ chức"
          />
        </label>
        <div className="grid grid-cols-2 gap-3 sm:col-span-2">
          <label className="text-sm font-semibold text-slate-300">
            Từ ngày
            <DateControl
              className={controlClass}
              defaultValue={parameters.publishedFrom}
              name="publishedFrom"
            />
          </label>
          <label className="text-sm font-semibold text-slate-300">
            Đến ngày
            <DateControl
              className={controlClass}
              defaultValue={parameters.publishedTo}
              name="publishedTo"
            />
          </label>
        </div>
        <label className="block text-sm font-semibold text-slate-300">
          Thông tin xác nhận
          <SelectControl
            className={controlClass}
            defaultValue={
              parameters.hasBlockchainProof === undefined
                ? ""
                : String(parameters.hasBlockchainProof)
            }
            name="hasBlockchainProof"
          >
            <option value="">Tất cả</option>
            <option value="true">Đã được xác nhận</option>
            <option value="false">Chưa được xác nhận</option>
          </SelectControl>
        </label>
        <label className="block text-sm font-semibold text-slate-300">
          Trạng thái chứng thư
          <SelectControl
            className={controlClass}
            defaultValue={parameters.certificateStatus ?? ""}
            name="certificateStatus"
          >
            <option value="">Tất cả</option>
            <option value="ACTIVE">Còn hiệu lực</option>
            <option value="EXPIRED">Hết hạn</option>
            <option value="REVOKED">Đã thu hồi</option>
          </SelectControl>
        </label>
        <Button className="w-full" type="submit">
          Áp dụng bộ lọc
        </Button>
        <Link
          className="flex min-h-11 items-center justify-center gap-2 text-sm font-semibold text-slate-400 transition hover:text-white"
          href="/search"
        >
          <RotateCcw aria-hidden="true" className="size-4" /> Xóa tất cả
        </Link>
      </form>
    </div>
  );
}

function HiddenSearchState({ parameters }: { parameters: SearchParameters }) {
  return (
    <>
      {parameters.q ? (
        <input name="q" type="hidden" value={parameters.q} />
      ) : null}
      {parameters.category ? (
        <input name="category" type="hidden" value={parameters.category} />
      ) : null}
      {parameters.tags.length ? (
        <input name="tags" type="hidden" value={parameters.tags.join(",")} />
      ) : null}
      <input name="sort" type="hidden" value={parameters.sort} />
    </>
  );
}

function FacetGroup({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <fieldset>
      <legend className="mb-3 text-xs font-bold tracking-[0.16em] text-slate-500 uppercase">
        {label}
      </legend>
      <div className="space-y-1">{children}</div>
    </fieldset>
  );
}

function FacetLink({
  active,
  count,
  href,
  label,
}: {
  active: boolean;
  count?: number;
  href: string;
  label: string;
}) {
  return (
    <Link
      aria-current={active ? "true" : undefined}
      className="flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm text-slate-300 transition hover:bg-white/[0.05] hover:text-white aria-current:bg-gold-300/10 aria-current:text-gold-200"
      href={href}
    >
      {active ? (
        <Check aria-hidden="true" className="size-4 text-gold-300" />
      ) : (
        <span className="size-4" />
      )}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count !== undefined ? (
        <span className="font-mono text-xs tabular-nums text-slate-600">
          {count}
        </span>
      ) : null}
    </Link>
  );
}
