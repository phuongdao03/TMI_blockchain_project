import type { Metadata } from "next";

import { SearchResultsPage } from "@/components/search/search-results-page";
import type {
  CertificateStatus,
  SearchParameters,
  SearchSort,
} from "@/lib/api/types";
import { getServerAuthState } from "@/lib/auth/server-session";

export const metadata: Metadata = {
  title: "Tìm kiếm tài sản công khai | TMI Certificate",
  description:
    "Tìm tác phẩm, chủ đề và chứng thư trong kho tài sản công khai TMI.",
  robots: { index: false, follow: true },
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const input = await searchParams;
  const authState = await getServerAuthState();
  const q = clean(input.q, 200);
  const parameters: SearchParameters = {
    q,
    category: slug(input.category),
    tags: tags(input.tags),
    tagsMode: first(input.tagsMode) === "all" ? "all" : "any",
    organization: slug(input.organization),
    publishedFrom: date(input.publishedFrom),
    publishedTo: date(input.publishedTo),
    hasBlockchainProof: boolean(input.hasBlockchainProof),
    certificateStatus: certificateStatus(input.certificateStatus),
    sort: sort(input.sort, Boolean(q)),
    cursor: clean(input.cursor, 1_024),
  };
  return (
    <main className="relative isolate overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[38rem] bg-[radial-gradient(circle_at_82%_4%,rgba(212,167,44,.11),transparent_25rem),radial-gradient(circle_at_6%_26%,rgba(220,38,38,.1),transparent_26rem)]"
      />
      <div className="mx-auto min-h-[calc(100dvh-5rem)] max-w-[90rem] px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
        <SearchResultsPage
          authenticated={Boolean(authState.user)}
          parameters={parameters}
        />
      </div>
    </main>
  );
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
function clean(value: string | string[] | undefined, max: number) {
  const result = first(value)?.trim().slice(0, max);
  return result || undefined;
}
function slug(value: string | string[] | undefined) {
  const result = clean(value, 160)?.toLowerCase();
  return result && /^[a-z0-9_-]+$/.test(result) ? result : undefined;
}
function tags(value: string | string[] | undefined) {
  return [
    ...new Set(
      (first(value) ?? "")
        .split(",")
        .map((item) => slug(item))
        .filter((item): item is string => Boolean(item)),
    ),
  ].slice(0, 10);
}
function date(value: string | string[] | undefined) {
  const result = first(value);
  return result && /^\d{4}-\d{2}-\d{2}$/.test(result) ? result : undefined;
}
function boolean(value: string | string[] | undefined) {
  const result = first(value);
  return result === "true" ? true : result === "false" ? false : undefined;
}
function certificateStatus(
  value: string | string[] | undefined,
): CertificateStatus | undefined {
  const result = first(value);
  return result === "ACTIVE" || result === "EXPIRED" || result === "REVOKED"
    ? result
    : undefined;
}
function sort(
  value: string | string[] | undefined,
  hasQuery: boolean,
): SearchSort {
  const result = first(value);
  if (result === "newest" || result === "oldest" || result === "most_viewed")
    return result;
  return hasQuery ? "relevance" : "newest";
}
