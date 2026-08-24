"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  FileSearch,
  History,
  LoaderCircle,
  Search,
  ShieldQuestion,
} from "lucide-react";
import { useState } from "react";

import { publicApi } from "@/lib/api/client";
import type { VerificationStatus } from "@/lib/api/types";
import {
  compareLocalFile,
  MAX_LOCAL_VERIFICATION_BYTES,
  type LocalFileComparison,
} from "@/lib/verification/file-hash";

type ComparisonState =
  | LocalFileComparison
  | { status: "PENDING_CONFIRMATION" | "CHAIN_UNAVAILABLE"; digest: null };

const resultCopy: Record<
  VerificationStatus,
  { title: string; detail: string; tone: string; icon: typeof CheckCircle2 }
> = {
  VALID: {
    title: "Dữ liệu đã được ghi nhận và không thay đổi",
    detail: "Thông tin hiện tại trùng với dấu xác nhận đã công bố.",
    tone: "text-emerald-300",
    icon: CheckCircle2,
  },
  MISMATCH: {
    title: "Dữ liệu đối chiếu không trùng khớp",
    detail:
      "Không nên sử dụng chứng thư này trước khi liên hệ đơn vị phát hành.",
    tone: "text-red-300",
    icon: AlertTriangle,
  },
  REVOKED: {
    title: "Chứng thư đã được thu hồi",
    detail: "Chứng thư không còn hiệu lực sử dụng.",
    tone: "text-red-300",
    icon: AlertTriangle,
  },
  EXPIRED: {
    title: "Chứng thư đã hết hạn",
    detail: "Hãy yêu cầu chủ thể cung cấp chứng thư còn hiệu lực.",
    tone: "text-amber-300",
    icon: AlertTriangle,
  },
  PENDING: {
    title: "Đang chờ xác nhận",
    detail: "Hệ thống chưa thể hoàn tất đối chiếu. Vui lòng thử lại sau.",
    tone: "text-amber-300",
    icon: LoaderCircle,
  },
  NOT_FOUND: {
    title: "Không tìm thấy chứng thư",
    detail: "Kiểm tra lại mã hoặc yêu cầu người gửi cung cấp liên kết hợp lệ.",
    tone: "text-slate-300",
    icon: ShieldQuestion,
  },
};

function formatDate(value: string | null) {
  if (!value) return "Chưa có thông tin";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function localComparisonError(error: unknown): string {
  if (!(error instanceof Error)) {
    return "Không thể đọc tệp để đối chiếu trên thiết bị này.";
  }
  if (error.message === "The selected file is empty.") {
    return "Tệp đã chọn đang trống. Hãy chọn lại tài liệu cần đối chiếu.";
  }
  if (error.message === "The selected file is too large.") {
    return `Tệp vượt quá giới hạn ${MAX_LOCAL_VERIFICATION_BYTES / 1024 / 1024} MB để đối chiếu tại máy.`;
  }
  if (error.message === "Secure local hashing is unavailable in this browser.") {
    return "Trình duyệt này chưa hỗ trợ đối chiếu cục bộ. Hãy cập nhật hoặc dùng trình duyệt khác.";
  }
  return "Không thể đọc tệp để đối chiếu trên thiết bị này.";
}

export function VerificationPanel({
  token,
  embedded = false,
  initialLookup = "",
}: {
  token?: string;
  embedded?: boolean;
  initialLookup?: string;
}) {
  const [mode, setMode] = useState<"number" | "transaction">("number");
  const [value, setValue] = useState(initialLookup);
  const [lookup, setLookup] = useState(token ?? initialLookup);
  const [comparison, setComparison] = useState<ComparisonState | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [documentIndex, setDocumentIndex] = useState(0);
  const result = useQuery({
    queryKey: ["public-verification", token ? "token" : mode, lookup],
    queryFn: () =>
      token
        ? publicApi.verifyToken(token)
        : mode === "number"
          ? publicApi.verifyNumber(lookup)
          : publicApi.verifyTransaction(lookup),
    enabled: Boolean(lookup),
    retry: false,
  });
  const certificateNumber = result.data?.certificateNumber;
  const publicDocuments = result.data?.documents ?? [];
  const activeDocumentIndex =
    documentIndex >= 0 && documentIndex < publicDocuments.length
      ? documentIndex
      : 0;
  const selectedPublicDocument = publicDocuments[activeDocumentIndex];
  const history = useQuery({
    queryKey: ["public-certificate-history", certificateNumber],
    queryFn: () => publicApi.certificateVersions(certificateNumber!),
    enabled: Boolean(certificateNumber),
    retry: false,
  });

  return (
    <div className="verification-panel space-y-8">
      <header className="max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
          Tra cứu độc lập
        </p>
        <h1
          className={`mt-4 font-bold tracking-tight text-white ${
            embedded ? "text-3xl sm:text-4xl" : "text-4xl sm:text-6xl"
          }`}
        >
          Kiểm tra chứng thư
        </h1>
        <p className="mt-5 text-base leading-7 text-slate-300">
          Nhập mã được cung cấp để xem tình trạng và thông tin xác nhận đã công
          bố.
        </p>
      </header>

      {!token ? (
        <form
          action="/verify"
          className="verification-form grid gap-3 border-y border-white/10 py-6 md:grid-cols-[12rem_1fr_auto]"
          method="get"
          onSubmit={(event) => {
            event.preventDefault();
            setComparison(null);
            setDocumentIndex(0);
            setLookup(value.trim());
          }}
        >
          <label className="sr-only" htmlFor="verification-mode">
            Cách tra cứu
          </label>
          <select
            className="verification-control min-h-12 rounded-xl border border-white/15 bg-ink-900 px-4 text-sm text-white"
            id="verification-mode"
            onChange={(event) => setMode(event.target.value as typeof mode)}
            value={mode}
          >
            <option value="number">Số chứng thư</option>
            <option value="transaction">Mã giao dịch</option>
          </select>
          <label className="sr-only" htmlFor="verification-value">
            Thông tin cần tra cứu
          </label>
          <input
            className="verification-control min-h-12 rounded-xl border border-white/15 bg-ink-950 px-4 text-sm text-white outline-none focus:border-gold-300"
            id="verification-value"
            name="lookup"
            onChange={(event) => setValue(event.target.value)}
            placeholder={mode === "number" ? "Ví dụ: TMI-2026-…" : "Ví dụ: 0x…"}
            required
            value={value}
          />
          <button
            className="verification-submit inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary-600 px-6 text-sm font-bold text-white"
            type="submit"
          >
            <Search className="size-4" /> Kiểm tra
          </button>
        </form>
      ) : null}

      <section aria-live="polite">
        {result.isFetching ? (
          <div className="grid min-h-72 place-items-center" role="status">
            <span className="flex items-center gap-2 text-sm text-slate-300">
              <LoaderCircle className="size-5 animate-spin" /> Đang kiểm tra…
            </span>
          </div>
        ) : result.error ? (
          <div className="border border-red-400/30 bg-red-400/5 p-6 text-red-200">
            Chưa thể kết nối dịch vụ. Vui lòng thử lại sau.
          </div>
        ) : result.data ? (
          <div className="space-y-8">
            <VerificationResult data={result.data} />

            {result.data.status !== "NOT_FOUND" ? (
              <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
                <section className="border-t border-white/15 pt-6">
                  <div className="flex items-center gap-3">
                    <FileSearch className="size-5 text-gold-300" />
                    <h2 className="text-xl font-bold text-white">
                      Đối chiếu tài liệu
                    </h2>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    Tệp được đối chiếu ngay trên thiết bị của bạn và không được
                    tải lên máy chủ. Tối đa 25 MB mỗi tệp.
                  </p>
                  {!publicDocuments.length ? (
                    <p
                      className="mt-5 rounded-xl border border-amber-300/20 bg-amber-300/5 px-4 py-3 text-sm leading-6 text-amber-100"
                      role="status"
                    >
                      Chứng thư này không công bố dấu vân tay tài liệu để đối
                      chiếu công khai.
                    </p>
                  ) : null}
                  {publicDocuments.length > 1 ? (
                    <div className="mt-5">
                      <label
                        className="text-xs font-bold text-slate-300"
                        htmlFor="verification-document"
                      >
                        Tài liệu cần đối chiếu
                      </label>
                      <select
                        className="mt-2 min-h-11 w-full rounded-xl border border-white/15 bg-ink-950 px-4 text-sm text-white"
                        id="verification-document"
                        onChange={(event) => {
                          setDocumentIndex(Number(event.target.value));
                          setComparison(null);
                          setComparisonError(null);
                        }}
                        value={activeDocumentIndex}
                      >
                        {publicDocuments.map((document, index) => (
                          <option
                            key={`${document.sha256}-${index}`}
                            value={index}
                          >
                            {document.title}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : null}
                  {selectedPublicDocument ? (
                    <label className="mt-5 inline-flex min-h-11 cursor-pointer items-center rounded-xl border border-white/15 px-4 text-sm font-bold text-white hover:bg-white/5">
                      Chọn tài liệu để đối chiếu
                      <input
                        aria-label="Chọn tài liệu để đối chiếu"
                        className="sr-only"
                        onChange={async (event) => {
                          const file = event.target.files?.[0];
                          if (!file) return;
                          setComparing(true);
                          setComparison(null);
                          setComparisonError(null);
                          try {
                            setComparison(
                              await compareLocalFile(file, [
                                selectedPublicDocument.sha256,
                              ]),
                            );
                          } catch (error) {
                            setComparisonError(localComparisonError(error));
                          } finally {
                            setComparing(false);
                          }
                        }}
                        type="file"
                      />
                    </label>
                  ) : null}
                  <ComparisonResult
                    comparison={comparison}
                    error={comparisonError}
                    pending={comparing}
                  />
                  <p className="mt-4 text-xs text-slate-400">
                    Giới hạn tệp đối chiếu: {MAX_LOCAL_VERIFICATION_BYTES / 1024 / 1024} MB.
                  </p>
                </section>

                <section className="border-t border-white/15 pt-6">
                  <div className="flex items-center gap-3">
                    <History className="size-5 text-gold-300" />
                    <h2 className="text-xl font-bold text-white">
                      Lịch sử xác nhận
                    </h2>
                  </div>
                  {history.isPending ? (
                    <p className="mt-4 text-sm text-slate-400">
                      Đang tải lịch sử…
                    </p>
                  ) : history.data?.length ? (
                    <ol className="mt-5 space-y-4">
                      {history.data.map((item) => (
                        <li
                          className="border-l-2 border-white/15 pl-4"
                          key={item.versionNo}
                        >
                          <p className="font-bold text-white">
                            Phiên bản {item.versionNo}
                          </p>
                          <p className="mt-1 text-sm text-slate-400">
                            {item.status === "ACTIVE"
                              ? "Đang có hiệu lực"
                              : item.status === "REVOKED"
                                ? "Đã thu hồi"
                                : "Đã được cập nhật"}
                            {" · "}
                            {formatDate(item.confirmedAt)}
                          </p>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-4 text-sm text-slate-400">
                      Chưa có lịch sử công khai bổ sung.
                    </p>
                  )}
                </section>
              </div>
            ) : null}

            <p className="border-t border-white/10 pt-5 text-xs leading-5 text-slate-400">
              Kết quả xác nhận dữ liệu số đã được ghi nhận tại một thời điểm. Nó
              không tự chứng minh tính xác thực vật lý, quyền sở hữu hoặc tính
              hợp pháp của tài sản.
            </p>
          </div>
        ) : (
          <div
            className={`grid place-items-center text-center text-slate-400 ${
              embedded ? "min-h-32 py-8" : "min-h-64"
            }`}
          >
            Nhập mã chứng thư hoặc mã giao dịch để bắt đầu.
          </div>
        )}
      </section>
    </div>
  );
}

function VerificationResult({
  data,
}: {
  data: Awaited<ReturnType<typeof publicApi.verifyNumber>>;
}) {
  const copy = resultCopy[data.status];
  const Icon = copy.icon;
  return (
    <section className="grid gap-6 border border-white/10 bg-white/[0.035] p-6 sm:p-8 lg:grid-cols-[1fr_1fr]">
      <div>
        <Icon
          className={`size-10 ${copy.tone} ${data.status === "PENDING" ? "animate-spin" : ""}`}
        />
        <p
          className={`mt-5 text-xs font-bold uppercase tracking-[0.18em] ${copy.tone}`}
        >
          Kết quả kiểm tra
        </p>
        <h2 className="mt-2 text-2xl font-bold text-white sm:text-3xl">
          {copy.title}
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">{copy.detail}</p>
      </div>
      <div>
        <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
          <Fact label="Chứng thư" value={data.certificateNumber} />
          <Fact label="Mã tài sản" value={data.dossierCode} />
          <Fact label="Tài sản" value={data.assetTitle} />
          <Fact
            label="Phiên bản"
            value={data.version ? String(data.version) : null}
          />
          <Fact label="Đơn vị xác nhận" value={data.issuerLabel} />
          <Fact
            label="Thời điểm xác nhận"
            value={formatDate(data.confirmedAt)}
          />
        </dl>
        <details className="mt-6 border-t border-white/10 pt-4 text-sm">
          <summary className="cursor-pointer font-bold text-slate-200">
            Xem thông tin đối chiếu nâng cao
          </summary>
          <dl className="mt-4 space-y-3 text-xs">
            <Fact label="Mạng ghi nhận" value={data.network} technical />
            <Fact
              label="Khối xác nhận"
              value={data.blockNumber ? String(data.blockNumber) : null}
              technical
            />
            <Fact label="Dấu dữ liệu" value={data.metadataHash} technical />
            <Fact label="Mã giao dịch" value={data.transactionHash} technical />
          </dl>
          {data.explorerUrl ? (
            <a
              className="mt-4 inline-flex items-center gap-2 text-gold-300"
              href={data.explorerUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              Xem bản ghi công khai <ExternalLink className="size-4" />
            </a>
          ) : null}
        </details>
      </div>
    </section>
  );
}

function Fact({
  label,
  value,
  technical = false,
}: {
  label: string;
  value?: string | null;
  technical?: boolean;
}) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-slate-400">{label}</dt>
      <dd
        className={`mt-1 break-all text-slate-200 ${technical ? "font-mono" : "font-bold"}`}
      >
        {value}
      </dd>
    </div>
  );
}

function ComparisonResult({
  comparison,
  error,
  pending,
}: {
  comparison: ComparisonState | null;
  error: string | null;
  pending: boolean;
}) {
  if (pending)
    return (
      <p className="mt-4 text-sm text-slate-300">
        Đang đối chiếu trên thiết bị…
      </p>
    );
  if (error)
    return (
      <p className="mt-4 text-sm text-red-300" role="alert">
        {error}
      </p>
    );
  if (!comparison) return null;
  if (comparison.status === "MATCH") {
    return (
      <p className="mt-4 flex items-center gap-2 text-sm font-bold text-emerald-300">
        <FileCheck2 className="size-4" /> Tài liệu trùng khớp
      </p>
    );
  }
  if (comparison.status === "NO_MATCH") {
    return (
      <p className="mt-4 text-sm font-bold text-red-300">
        Tài liệu đã thay đổi hoặc không thuộc bộ công khai này
      </p>
    );
  }
  if (comparison.status === "PENDING_CONFIRMATION") {
    return (
      <p className="mt-4 text-sm text-amber-300">
        Bằng chứng đang được hoàn tất. Vui lòng thử lại sau.
      </p>
    );
  }
  if (comparison.status === "CHAIN_UNAVAILABLE") {
    return (
      <p className="mt-4 text-sm text-amber-300">
        Tạm thời chưa thể xác nhận. Vui lòng thử lại sau.
      </p>
    );
  }
  return (
    <p className="mt-4 text-sm text-amber-300">
      Chứng thư này không có tài liệu công khai để đối chiếu.
    </p>
  );
}
