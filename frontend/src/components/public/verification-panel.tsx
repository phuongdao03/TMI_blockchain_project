"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  History,
  LoaderCircle,
  Search,
  ShieldQuestion,
} from "lucide-react";
import { useState } from "react";

import { publicApi } from "@/lib/api/client";
import { DigitalCertificate } from "@/components/public/digital-certificate";
import { SelectControl } from "@/components/ui/form-controls";
import type { VerificationStatus } from "@/lib/api/types";

const resultCopy: Record<
  VerificationStatus,
  { title: string; detail: string; tone: string; icon: typeof CheckCircle2 }
> = {
  VALID: {
    title: "Chứng thư hợp lệ và đã được xác nhận trên blockchain.",
    detail:
      "Thông tin chứng thư trùng khớp với bản ghi công khai. Bạn có thể xem tài sản, thời điểm xác nhận và mã giao dịch ở bên cạnh.",
    tone: "text-success",
    icon: CheckCircle2,
  },
  MISMATCH: {
    title: "Tài liệu hiện tại không trùng với dấu vân tay đã công bố.",
    detail: "Hãy kiểm tra lại tài liệu hoặc liên hệ đơn vị phát hành.",
    tone: "text-error",
    icon: AlertTriangle,
  },
  REVOKED: {
    title: "Chứng thư đã được thu hồi",
    detail: "Chứng thư không còn hiệu lực sử dụng.",
    tone: "text-error",
    icon: AlertTriangle,
  },
  EXPIRED: {
    title: "Chứng thư đã hết hạn",
    detail: "Hãy yêu cầu chủ thể cung cấp chứng thư còn hiệu lực.",
    tone: "text-warning",
    icon: AlertTriangle,
  },
  PENDING: {
    title: "Đang chờ xác nhận",
    detail: "Giao dịch đã gửi, đang chờ mạng Polygon xác nhận.",
    tone: "text-warning",
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

function networkLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.toLowerCase() === "polygon"
    ? "Polygon (sổ ghi nhận công khai)"
    : value;
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
            embedded ? "text-3xl sm:text-4xl" : "text-3xl sm:text-6xl"
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
            setLookup(value.trim());
          }}
        >
          <label className="sr-only" htmlFor="verification-mode">
            Cách tra cứu
          </label>
          <SelectControl
            className="verification-control min-h-12 rounded-xl border border-white/15 bg-ink-900 px-4 text-sm text-white"
            id="verification-mode"
            onChange={(event) => setMode(event.target.value as typeof mode)}
            value={mode}
          >
            <option value="number">Số chứng thư</option>
            <option value="transaction">Mã giao dịch</option>
          </SelectControl>
          <label className="sr-only" htmlFor="verification-value">
            Thông tin cần tra cứu
          </label>
          <input
            className="verification-control min-h-12 rounded-xl border border-white/15 bg-ink-950 px-4 text-sm text-white outline-none focus:border-gold-300"
            id="verification-value"
            name="lookup"
            onChange={(event) => setValue(event.target.value)}
            placeholder={mode === "number" ? "Ví dụ: CNS-2026-…" : "Ví dụ: 0x…"}
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
            Chưa thể kiểm tra blockchain. Vui lòng thử lại sau.
          </div>
        ) : result.data ? (
          <div className="space-y-8">
            <VerificationResult data={result.data} />

            {result.data.status !== "NOT_FOUND" ? (
              <DigitalCertificate data={result.data} />
            ) : null}

            {result.data.status !== "NOT_FOUND" ? (
              <div>
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
  const detail =
    data.status === "PENDING" && data.networkAvailable === false
      ? "Bản ghi chứng thư vẫn còn trong hệ thống. Polygon đang tạm thời không phản hồi nên chưa thể đối chiếu trực tiếp; vui lòng thử lại sau."
      : copy.detail;
  const Icon = copy.icon;
  return (
    <section className="grid gap-6 border-y border-white/10 py-6 sm:py-8 lg:grid-cols-[1fr_1fr]">
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
        <p className="mt-3 text-sm leading-6 text-slate-400">{detail}</p>
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
          <Fact
            label="Nơi ghi nhận công khai"
            value={networkLabel(data.network)}
          />
          <Fact
            label="Mức xác nhận"
            value={
              data.confirmations !== undefined
                ? `${data.confirmations} lượt xác nhận từ mạng`
                : null
            }
          />
        </dl>
        <details className="mt-6 border-t border-white/10 pt-4 text-sm">
          <summary className="cursor-pointer font-bold text-slate-200">
            Chi tiết nâng cao
          </summary>
          <dl className="mt-4 space-y-3 text-xs">
            <Fact label="Mạng ghi nhận" value={data.network} technical />
            <Fact
              label="Số lượt mạng đã xác nhận"
              value={String(data.confirmations)}
              technical
            />
            <Fact
              label="Số khối ghi nhận"
              value={data.blockNumber ? String(data.blockNumber) : null}
              technical
            />
            <Fact
              label="Dấu vân tay số của hồ sơ"
              value={data.metadataHash}
              technical
            />
            <Fact
              label="Mã giao dịch trên blockchain"
              value={data.transactionHash}
              technical
            />
            <Fact
              label="Địa chỉ sổ đăng ký công khai"
              value={data.contractAddress}
              technical
            />
            <Fact
              label="Ví tổ chức đã ký"
              value={data.signerWalletAddress}
              technical
            />
            <Fact
              label="Sự kiện ghi nhận"
              value={data.eventName ?? "ProofRecorded"}
              technical
            />
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
        <details className="mt-4 border-t border-white/10 pt-4 text-sm">
          <summary className="cursor-pointer font-bold text-slate-200">
            Blockchain là gì?
          </summary>
          <p className="mt-3 leading-6 text-slate-400">
            Blockchain là sổ ghi nhận công khai. Hệ thống không đưa tài liệu gốc
            lên mạng; chỉ ghi lại dấu vân tay số để kiểm tra tài liệu có bị thay
            đổi hay không.
          </p>
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
