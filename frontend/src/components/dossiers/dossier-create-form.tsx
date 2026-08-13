"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, FilePlus2, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { ApiError, dossierApi } from "@/lib/api/client";
import { dossierKeys } from "@/lib/dossiers/query-keys";

export const DIGITAL_ASSET_CATEGORY_ID = "4d28db19-1507-5a45-a50d-cd0aa83029ec";

const schema = z.object({
  title: z.string().trim().min(3, "Tên hồ sơ cần ít nhất 3 ký tự.").max(255),
  summary: z.string().trim().max(10_000).optional(),
  visibility: z.enum(["PRIVATE", "UNLISTED", "PUBLIC"]),
});

type FormValues = z.infer<typeof schema>;

export function DossierCreateForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      summary: "",
      visibility: "PRIVATE",
    },
  });
  const create = useMutation({
    mutationFn: dossierApi.create,
    onSuccess: async (dossier) => {
      await queryClient.invalidateQueries({ queryKey: dossierKeys.lists() });
      router.push(`/dossiers/${dossier.id}`);
    },
  });

  const submit = form.handleSubmit((values) => {
    create.mutate({
      categoryId: DIGITAL_ASSET_CATEGORY_ID,
      title: values.title,
      summary: values.summary || null,
      visibility: values.visibility,
    });
  });

  return (
    <form className="space-y-6" onSubmit={submit}>
      <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-100 bg-neutral-50/70 px-5 py-4 sm:px-6">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Danh mục hồ sơ
          </p>
        </div>
        <div className="flex items-start gap-4 p-5 sm:p-6">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700">
            <ShieldCheck aria-hidden="true" className="size-5" />
          </span>
          <div>
            <h2 className="font-bold text-neutral-950">Tài sản trí tuệ số</h2>
            <p className="mt-1 text-sm leading-6 text-neutral-500">
              Hồ sơ đề nghị xác lập nguồn gốc và bằng chứng cho tác phẩm, thương
              hiệu hoặc tài sản số.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-5 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div>
          <label
            className="text-sm font-bold text-neutral-900"
            htmlFor="dossier-title"
          >
            Tên tài sản hoặc tác phẩm
          </label>
          <input
            aria-describedby="dossier-title-error"
            className="mt-2 min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-4 text-sm outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
            id="dossier-title"
            placeholder="Ví dụ: Bộ nhận diện thương hiệu TMI"
            {...form.register("title")}
          />
          {form.formState.errors.title ? (
            <p
              className="mt-2 text-sm font-medium text-error"
              id="dossier-title-error"
              role="alert"
            >
              {form.formState.errors.title.message}
            </p>
          ) : null}
        </div>

        <div>
          <label
            className="text-sm font-bold text-neutral-900"
            htmlFor="dossier-summary"
          >
            Mô tả ngắn
          </label>
          <textarea
            className="mt-2 min-h-32 w-full resize-y rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm leading-6 outline-none transition focus:border-primary-500 focus:ring-4 focus:ring-primary-100"
            id="dossier-summary"
            placeholder="Nêu mục đích, nguồn gốc và phạm vi tài sản cần xác lập."
            {...form.register("summary")}
          />
        </div>

        <fieldset>
          <legend className="text-sm font-bold text-neutral-900">
            Chế độ hiển thị
          </legend>
          <div className="mt-2 grid gap-3 sm:grid-cols-3">
            {[
              ["PRIVATE", "Riêng tư", "Chỉ chủ hồ sơ và người xử lý"],
              ["UNLISTED", "Không niêm yết", "Chỉ người có liên kết"],
              ["PUBLIC", "Công khai", "Có thể công bố sau cấp chứng thư"],
            ].map(([value, label, description]) => (
              <label
                className="cursor-pointer rounded-xl border border-neutral-200 p-4 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50"
                key={value}
              >
                <input
                  className="accent-primary-600"
                  type="radio"
                  value={value}
                  {...form.register("visibility")}
                />
                <span className="ml-2 text-sm font-bold">{label}</span>
                <span className="mt-1 block pl-6 text-xs leading-5 text-neutral-500">
                  {description}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {create.error ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800"
          role="alert"
        >
          <p>
            {create.error instanceof ApiError &&
            create.error.code === "APPLICANT_PROFILE_INCOMPLETE"
              ? create.error.message
              : "Không thể tạo hồ sơ. Vui lòng kiểm tra dữ liệu và thử lại."}
          </p>
          {create.error instanceof ApiError &&
          create.error.code === "APPLICANT_PROFILE_INCOMPLETE" ? (
            <a
              className="mt-2 inline-block font-bold underline"
              href="/account"
            >
              Hoàn thiện hồ sơ tài khoản
            </a>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col-reverse justify-end gap-3 sm:flex-row">
        <Button className="min-w-44" disabled={create.isPending} type="submit">
          <FilePlus2 aria-hidden="true" className="size-4" />
          {create.isPending ? "Đang tạo…" : "Tạo hồ sơ nháp"}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Button>
      </div>
    </form>
  );
}
