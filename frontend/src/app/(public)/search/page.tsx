import { redirect } from "next/navigation";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const input = await searchParams;
  const query = new URLSearchParams();
  const keyword = first(input.q) ?? first(input.query);
  const category = first(input.category);
  const tag = first(input.tag) ?? first(input.tags)?.split(",")[0];

  if (keyword) query.set("query", keyword);
  if (category) query.set("category", category);
  if (tag) query.set("tag", tag);

  redirect(`/works${query.size ? `?${query}` : ""}`);
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
