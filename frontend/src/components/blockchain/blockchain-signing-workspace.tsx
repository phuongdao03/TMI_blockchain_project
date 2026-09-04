"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Circle,
  Copy,
  ExternalLink,
  FileCheck2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  proofRegistrySigningApi,
  walletLinkApi,
} from "@/lib/api/client";
import type {
  THVProofRegistryIntent,
  THVProofRegistryQueueItem,
} from "@/lib/api/types";
import {
  connectWallet,
  connectWalletWithConnector,
  currentWallet,
  sendTransaction,
  signWalletChallenge,
  subscribeWalletChanges,
  switchChain,
  walletOptions,
  walletErrorCode,
} from "@/lib/blockchain/eip1193";

type ConnectedWallet = { address: string; chainId: number } | null;

const statusLabel: Record<string, string> = {
  CREATED: "Chờ ký",
  SIGNING: "Đang chờ xác nhận ví",
  BROADCAST: "Đang chờ Polygon xác nhận",
  CONFIRMED: "Đã ghi nhận",
  FAILED: "Cần xử lý lại",
  REPLACED: "Đã được thay thế",
};
const terminalStatuses = new Set(["CONFIRMED", "FAILED", "REPLACED"]);
const signingSteps = [
  "Chuẩn bị",
  "Chờ MetaMask",
  "Đang xác nhận",
  "Đã ghi nhận",
] as const;

function compactAddress(address: string) {
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function errorMessage(error: unknown) {
  const walletError = error as { code?: number | string; message?: string };
  const providerCode = walletErrorCode(error);
  if (providerCode === "NO_WALLET") {
    return "KhÃ´ng tÃ¬m tháº¥y vÃ­. HÃ£y cÃ i Ä‘áº·t vÃ  má»Ÿ khÃ³a MetaMask, Rabby hoáº·c Coinbase Wallet.";
  }
  if (providerCode === "REQUEST_PENDING") {
    return "VÃ­ Ä‘ang cÃ³ yÃªu cáº§u chÆ°a xá»­ lÃ½. HÃ£y má»Ÿ cá»­a sá»• vÃ­ Ä‘á»ƒ xÃ¡c nháº­n hoáº·c há»§y yÃªu cáº§u Ä‘Ã³.";
  }
  if (providerCode === "UNAUTHORIZED") {
    return "Website chÆ°a Ä‘Æ°á»£c vÃ­ cho phÃ©p truy cáº­p. HÃ£y káº¿t ná»‘i láº¡i trong vÃ­.";
  }
  if (providerCode === "DISCONNECTED" || providerCode === "CHAIN_UNAVAILABLE") {
    return "VÃ­ Ä‘Ã£ ngáº¯t káº¿t ná»‘i. HÃ£y má»Ÿ khÃ³a vÃ­ vÃ  thá»­ káº¿t ná»‘i láº¡i.";
  }
  if (walletError?.code === 4001 || walletError?.code === "ACTION_REJECTED") {
    return "Bạn đã từ chối yêu cầu ký trong MetaMask. Giao dịch chưa được gửi.";
  }
  if (
    walletError?.code === -32000 ||
    walletError?.message?.toLowerCase().includes("insufficient funds")
  ) {
    return "Ví không đủ MATIC để trả phí gas. Hãy nạp thêm MATIC rồi thử lại.";
  }
  return "Chưa thể hoàn tất thao tác. Vui lòng thử lại hoặc liên hệ bộ phận vận hành.";
}

function signingStep(status: string, busy: "connect" | "link" | "sign" | null) {
  if (status === "CONFIRMED") return 3;
  if (status === "BROADCAST" || status === "FAILED") return 2;
  if (status === "SIGNING" || busy === "sign") return 1;
  return 0;
}

function verificationMessage(status: string) {
  if (status === "CONFIRMED") {
    return "Tài liệu đã được ghi nhận và chưa bị thay đổi.";
  }
  if (status === "BROADCAST" || status === "SIGNING") {
    return "Giao dịch đã gửi, đang chờ mạng Polygon xác nhận.";
  }
  if (status === "FAILED") {
    return "Giao dịch chưa được ghi nhận. Vui lòng kiểm tra lỗi và thử lại.";
  }
  return "Hồ sơ đã sẵn sàng. Hãy kiểm tra thông tin trước khi ký.";
}

function estimatedGasFee(intent: THVProofRegistryIntent | null) {
  if (!intent) return "Ước tính khi chuẩn bị giao dịch";
  const value =
    (intent.estimatedGas * intent.gasPriceWei) / 1_000_000_000_000_000_000;
  return `Tối đa khoảng ${value.toLocaleString("vi-VN", { maximumFractionDigits: 6 })} MATIC`;
}

export function BlockchainSigningWorkspace() {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState<ConnectedWallet>(null);
  const [selected, setSelected] = useState<THVProofRegistryQueueItem | null>(
    null,
  );
  const [preparedIntent, setPreparedIntent] =
    useState<THVProofRegistryIntent | null>(null);
  const [busy, setBusy] = useState<"connect" | "link" | "sign" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [copiedTransaction, setCopiedTransaction] = useState(false);
  const [walletPickerOpen, setWalletPickerOpen] = useState(false);

  const wallet = useQuery({
    queryKey: ["blockchain", "wallet"],
    queryFn: walletLinkApi.currentWallet,
    retry: false,
  });
  const queue = useQuery({
    queryKey: ["blockchain", "proof-registry", "signing-queue"],
    queryFn: proofRegistrySigningApi.queue,
    enabled: Boolean(wallet.data),
    retry: false,
    refetchInterval: 20_000,
  });
  const transactionStatus = useQuery({
    queryKey: [
      "blockchain",
      "proof-registry",
      "transaction",
      selected?.transactionId,
    ],
    queryFn: () => proofRegistrySigningApi.status(selected!.transactionId!),
    enabled: Boolean(
      selected?.transactionId && !terminalStatuses.has(selected.status),
    ),
    retry: false,
    refetchInterval: (query) =>
      query.state.data && terminalStatuses.has(query.state.data.status)
        ? false
        : 5_000,
  });

  const displayedSelected =
    selected && transactionStatus.data?.transactionId === selected.transactionId
      ? {
          ...selected,
          status: transactionStatus.data.status,
          txHash: transactionStatus.data.txHash,
          confirmations: transactionStatus.data.confirmations,
          errorCode: transactionStatus.data.errorCode,
        }
      : selected;

  useEffect(() => {
    const next = transactionStatus.data;
    if (!next) return;
    if (terminalStatuses.has(next.status)) {
      void queryClient.invalidateQueries({
        queryKey: ["blockchain", "proof-registry", "signing-queue"],
      });
    }
  }, [queryClient, transactionStatus.data]);

  const refreshWalletState = useCallback(async () => {
    try {
      const next = await currentWallet();
      setConnected(
        next.address ? { address: next.address, chainId: next.chainId } : null,
      );
    } catch {
      setConnected(null);
    }
  }, []);

  useEffect(() => {
    try {
      return subscribeWalletChanges(() => {
        setMessage(
          "Trạng thái ví đã thay đổi. Vui lòng kiểm tra lại trước khi ký.",
        );
        void refreshWalletState();
        void queryClient.invalidateQueries({ queryKey: ["blockchain"] });
      });
    } catch {
      return undefined;
    }
  }, [queryClient, refreshWalletState]);

  async function handleConnect() {
    setBusy("connect");
    setMessage(null);
    const options = walletOptions?.() ?? [];
    if (options.length > 1) {
      setBusy(null);
      setWalletPickerOpen(true);
      return;
    }
    try {
      setConnected(await connectWallet());
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function handleConnectWithConnector(connectorId: string) {
    setBusy("connect");
    setMessage(null);
    try {
      setConnected(await connectWalletWithConnector(connectorId));
      setWalletPickerOpen(false);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  async function handleVerifyWallet() {
    if (!connected) return;
    if (wallet.data && wallet.data.walletAddress !== connected.address) {
      setMessage("Ví đang kết nối không trùng với ví đã được xác minh.");
      return;
    }
    setBusy("link");
    setMessage(null);
    try {
      const challenge = await walletLinkApi.issueWalletChallenge(
        connected.address,
        connected.chainId,
      );
      const signature = await signWalletChallenge(
        challenge.message,
        connected.address,
      );
      await walletLinkApi.verifyWalletLink({
        challengeId: challenge.id,
        nonce: challenge.nonce,
        signature,
      });
      await queryClient.invalidateQueries({ queryKey: ["blockchain"] });
      setMessage("Ví của tổ chức đã được xác minh và sẵn sàng sử dụng.");
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  function openItem(item: THVProofRegistryQueueItem) {
    setSelected(item);
    setPreparedIntent(null);
    setMessage(null);
    setCopiedTransaction(false);
  }

  async function copyTransactionHash(transactionHash: string) {
    await navigator.clipboard.writeText(transactionHash);
    setCopiedTransaction(true);
  }

  async function handleSign() {
    if (!selected || !connected) return;
    if (!wallet.data || wallet.data.walletAddress !== connected.address) {
      setMessage("Hãy kết nối đúng ví đã được xác minh trước khi ký.");
      return;
    }
    if (connected.chainId !== wallet.data.chainId) {
      setMessage(
        "Ví đang ở sai mạng. Hãy chuyển sang mạng blockchain của THV.",
      );
      return;
    }
    setBusy("sign");
    setMessage(null);
    try {
      const intent = await proofRegistrySigningApi.prepareIntent(
        selected.dossierId,
        selected.version,
        connected.address,
      );
      setPreparedIntent(intent);
      const transactionHash = await sendTransaction(intent.transactionRequest);
      const submitted = await proofRegistrySigningApi.submitTransaction({
        transactionId: intent.transactionId,
        intentId: intent.intentId,
        transactionHash,
        connectedWallet: connected.address,
      });
      setSelected((current) =>
        current
          ? {
              ...current,
              transactionId: submitted.transactionId,
              status: submitted.status,
              txHash: submitted.txHash,
              confirmations: submitted.confirmations,
              errorCode: submitted.errorCode,
            }
          : current,
      );
      setMessage(
        "Yêu cầu đã được gửi. Hệ thống đang chờ mạng Polygon xác nhận kết quả.",
      );
      await queryClient.invalidateQueries({
        queryKey: ["blockchain", "proof-registry", "signing-queue"],
      });
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(null);
    }
  }

  const requiredChain = wallet.data?.chainId;
  const isWrongNetwork = Boolean(
    connected && requiredChain && connected.chainId !== requiredChain,
  );
  const isWrongWallet = Boolean(
    connected && wallet.data && connected.address !== wallet.data.walletAddress,
  );

  if (wallet.isPending)
    return <p role="status">Đang chuẩn bị khu vực ghi nhận hồ sơ…</p>;
  if (wallet.error) {
    const apiError = wallet.error instanceof ApiError ? wallet.error : null;
    const isForbidden = apiError?.status === 403;
    const title = isForbidden
      ? "Tài khoản chưa được phân quyền"
      : "Chưa thể mở khu vực ghi nhận";
    const description = isForbidden
      ? "Tài khoản hiện tại chưa được giao nhiệm vụ ghi nhận hồ sơ. Vui lòng liên hệ quản trị viên để kiểm tra phạm vi công việc."
      : "Khu vực ghi nhận đang tạm gián đoạn. Vui lòng thử lại sau hoặc báo bộ phận vận hành.";
    return (
      <section className="blockchain-error-state mx-auto max-w-3xl rounded-2xl border p-7">
        <ShieldCheck className="size-6" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-bold">{title}</h1>
        <p className="mt-2 leading-7">{description}</p>
        <button
          className="mt-5 min-h-11 rounded-lg border px-4 text-sm font-bold transition-colors"
          onClick={() => void wallet.refetch()}
          type="button"
        >
          Thử kiểm tra lại
        </button>
      </section>
    );
  }

  return (
    <div className="blockchain-signing-workspace mx-auto max-w-7xl space-y-6">
      <header className="rounded-3xl bg-neutral-950 px-7 py-8 text-white sm:px-10 sm:py-10">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary-300">
          Ghi nhận hồ sơ đã phê duyệt
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-5xl">
              Hồ sơ chờ ghi nhận
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              Dùng ví của tổ chức để xác nhận hồ sơ đã hoàn tất xét duyệt. Hệ
              thống chỉ công bố dấu vân tay số để kiểm tra tính toàn vẹn; tài
              liệu gốc và dữ liệu cá nhân vẫn được lưu trong hệ thống TMI.
            </p>
          </div>
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-white px-4 text-sm font-bold text-neutral-950 hover:bg-neutral-100 disabled:opacity-60"
            disabled={busy === "connect"}
            onClick={() => void handleConnect()}
            type="button"
          >
            {busy === "connect" ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : (
              <WalletCards className="size-4" aria-hidden="true" />
            )}
            {connected ? "Kết nối lại ví" : "Kết nối ví"}
          </button>
        </div>
      </header>

      {message ? (
        <p
          className="rounded-xl border border-primary-200 bg-primary-50 px-5 py-4 text-sm leading-6 text-primary-950"
          role="status"
        >
          {message}
        </p>
      ) : null}

      {walletPickerOpen ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="wallet-picker-title"
        >
          <div className="w-full max-w-md rounded-2xl bg-white p-6 text-neutral-950 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="wallet-picker-title" className="text-xl font-bold">
                  Chọn ví để kết nối
                </h2>
                <p className="mt-1 text-sm text-neutral-600">
                  Bạn có thể dùng MetaMask, Rabby, Coinbase hoặc WalletConnect.
                </p>
              </div>
              <button
                type="button"
                className="min-h-11 rounded-lg border px-3 text-sm font-semibold"
                onClick={() => setWalletPickerOpen(false)}
              >
                Đóng
              </button>
            </div>
            <div className="mt-5 grid gap-3">
              {walletOptions().map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className="flex min-h-12 items-center gap-3 rounded-xl border px-4 text-left font-semibold transition-colors hover:bg-neutral-100 disabled:opacity-60"
                  disabled={busy === "connect"}
                  onClick={() => void handleConnectWithConnector(option.id)}
                >
                  {option.icon ? (
                    <Image
                      src={option.icon}
                      alt=""
                      className="size-6"
                      height={24}
                      unoptimized
                      width={24}
                    />
                  ) : (
                    <WalletCards className="size-5" aria-hidden="true" />
                  )}
                  <span>{option.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <section>
        <article className="blockchain-surface rounded-2xl border p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
                Ví ký của tổ chức
              </p>
              <h2 className="mt-2 text-xl font-bold text-neutral-950">
                {wallet.data
                  ? compactAddress(wallet.data.walletAddress)
                  : "Chưa xác minh ví"}
              </h2>
            </div>
            <ShieldCheck
              className="size-6 text-primary-700"
              aria-hidden="true"
            />
          </div>
          <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-neutral-500">Mạng yêu cầu</dt>
              <dd className="mt-1 font-bold text-neutral-950">
                {requiredChain === 137 ? "Polygon Mainnet" : "Chưa xác định"}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-neutral-500">Ví đang kết nối</dt>
              <dd className="mt-1 font-bold text-neutral-950">
                {connected ? compactAddress(connected.address) : "Chưa kết nối"}
              </dd>
            </div>
          </dl>
          {isWrongWallet || isWrongNetwork ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <div className="flex gap-2 font-bold">
                <AlertTriangle className="size-4" aria-hidden="true" />
                {isWrongWallet ? "Sai tài khoản ví" : "Sai mạng blockchain"}
              </div>
              {isWrongNetwork && requiredChain ? (
                <button
                  className="mt-3 rounded-lg bg-amber-900 px-3 py-2 text-xs font-bold text-white"
                  onClick={() =>
                    void switchChain(requiredChain)
                      .then(refreshWalletState)
                      .catch((error: unknown) =>
                        setMessage(errorMessage(error)),
                      )
                  }
                  type="button"
                >
                  Chuyển sang mạng yêu cầu
                </button>
              ) : null}
            </div>
          ) : null}
          {!wallet.data && connected ? (
            <button
              className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white disabled:opacity-60"
              disabled={busy === "link"}
              onClick={() => void handleVerifyWallet()}
              type="button"
            >
              {busy === "link" ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <BadgeCheck className="size-4" />
              )}
              Xác minh ví của tổ chức
            </button>
          ) : null}
        </article>
      </section>

      <section className="blockchain-surface rounded-2xl border">
        <div className="flex items-center justify-between gap-4 border-b border-[var(--theme-border)] px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
              Hồ sơ đã sẵn sàng
            </p>
            <h2 className="mt-1 text-xl font-bold text-neutral-950">
              Hồ sơ chờ bạn ký
            </h2>
          </div>
          <button
            className="inline-flex items-center gap-2 text-sm font-bold text-primary-700 disabled:opacity-50"
            disabled={!wallet.data}
            onClick={() => void queue.refetch()}
            type="button"
          >
            <RefreshCw className="size-4" /> Làm mới
          </button>
        </div>
        {!wallet.data ? (
          <p className="p-6 text-sm text-neutral-600">
            Kết nối và xác minh ví để mở hàng đợi ký.
          </p>
        ) : null}
        {wallet.data && queue.isPending ? (
          <p className="p-6 text-sm text-neutral-600">Đang tải hàng đợi…</p>
        ) : null}
        {wallet.data && queue.error ? (
          <p className="p-6 text-sm text-rose-700">
            {errorMessage(queue.error)}
          </p>
        ) : null}
        {wallet.data && queue.data?.length === 0 ? (
          <p className="p-6 text-sm text-neutral-600">
            Không có hồ sơ nào đang chờ ký.
          </p>
        ) : null}
        <div className="divide-y divide-neutral-100">
          {queue.data?.map((item) => (
            <button
              className="blockchain-queue-item grid w-full gap-3 px-6 py-5 text-left transition md:grid-cols-[1fr_auto] md:items-center"
              key={`${item.dossierId}:${item.version}`}
              onClick={() => openItem(item)}
              type="button"
            >
              <div>
                <p className="font-mono text-xs font-bold text-primary-700">
                  {item.dossierCode} · V{item.version}
                </p>
                <h3 className="mt-1 text-base font-bold text-neutral-950">
                  {item.dossierTitle}
                </h3>
                <p className="mt-1 text-sm text-neutral-600">
                  Được chuyển sang chờ ghi nhận lúc {formatDate(item.createdAt)}
                </p>
              </div>
              <span className="rounded-full bg-primary-50 px-3 py-1.5 text-xs font-bold text-primary-800">
                {statusLabel[item.status] ?? item.status}
              </span>
            </button>
          ))}
        </div>
      </section>

      {displayedSelected ? (
        <section className="blockchain-surface rounded-2xl border p-6 sm:p-8">
          <div className="flex items-start justify-between gap-5">
            <div>
              <p className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
                Xác nhận trước khi ký
              </p>
              <h2 className="mt-2 text-2xl font-bold text-neutral-950">
                {displayedSelected.dossierTitle}
              </h2>
              <p className="mt-2 text-sm text-neutral-600">
                {displayedSelected.dossierCode} · Phiên bản{" "}
                {displayedSelected.version}
              </p>
            </div>
            <span className="rounded-full bg-neutral-100 px-3 py-1.5 text-xs font-bold text-neutral-700">
              {statusLabel[displayedSelected.status] ??
                displayedSelected.status}
            </span>
          </div>
          <ol
            aria-label="Tiến trình ký"
            className="mt-7 grid gap-2 sm:grid-cols-4"
          >
            {signingSteps.map((step, index) => {
              const currentStep = signingStep(displayedSelected.status, busy);
              const complete = index < currentStep || currentStep === 3;
              const current = index === currentStep;
              return (
                <li
                  aria-current={current ? "step" : undefined}
                  className={`flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2 text-xs font-bold ${
                    current
                      ? "border-primary-600 bg-primary-50 text-primary-950"
                      : complete
                        ? "border-primary-200 bg-primary-50 text-primary-800"
                        : "border-neutral-200 text-neutral-500"
                  }`}
                  key={step}
                >
                  {complete ? (
                    <CheckCircle2
                      className="size-4 shrink-0"
                      aria-hidden="true"
                    />
                  ) : current ? (
                    <LoaderCircle
                      className="size-4 shrink-0"
                      aria-hidden="true"
                    />
                  ) : (
                    <Circle className="size-4 shrink-0" aria-hidden="true" />
                  )}
                  {step}
                </li>
              );
            })}
          </ol>

          <div
            className="blockchain-soft-surface mt-5 rounded-xl border p-4"
            role="status"
          >
            <p className="font-bold text-neutral-950">
              {verificationMessage(displayedSelected.status)}
            </p>
            {displayedSelected.status === "BROADCAST" ? (
              <p className="mt-1 text-sm text-neutral-600">
                Hệ thống tự kiểm tra kết quả định kỳ. Trạng thái chỉ chuyển
                thành “Đã ghi nhận” sau khi mạng Polygon xác nhận hoàn tất.
              </p>
            ) : null}
          </div>

          <dl className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Mạng blockchain</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                Polygon Mainnet
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Ví đang sử dụng</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {connected ? compactAddress(connected.address) : "Chưa kết nối"}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Hồ sơ và phiên bản</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {displayedSelected.dossierCode} · V{displayedSelected.version}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Phí gas dự kiến</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {estimatedGasFee(preparedIntent)}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4 sm:col-span-2 xl:col-span-4">
              <dt className="text-xs text-neutral-500">
                Dấu vân tay số của hồ sơ
              </dt>
              <dd className="mt-2 break-all font-mono text-xs text-neutral-900">
                {displayedSelected.proofHash}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">
                Số lượt mạng đã xác nhận
              </dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {displayedSelected.confirmations}
              </dd>
            </div>
          </dl>
          {displayedSelected.txHash ? (
            <div className="mt-5 rounded-xl border border-neutral-200 p-4">
              <p className="text-xs text-neutral-500">
                Mã giao dịch trên blockchain
              </p>
              <p className="mt-2 break-all font-mono text-xs text-neutral-700">
                {displayedSelected.txHash}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800"
                  onClick={() =>
                    void copyTransactionHash(displayedSelected.txHash!)
                  }
                  type="button"
                >
                  <Copy className="size-4" aria-hidden="true" />
                  Sao chép mã giao dịch
                </button>
                <a
                  className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800"
                  href={`https://polygonscan.com/tx/${displayedSelected.txHash}`}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="size-4" aria-hidden="true" />
                  Mở giao dịch trên PolygonScan
                </a>
              </div>
              {copiedTransaction ? (
                <p className="mt-2 text-sm text-primary-800" role="status">
                  Đã sao chép mã giao dịch.
                </p>
              ) : null}
            </div>
          ) : null}
          <details className="mt-5 rounded-xl border border-neutral-200 p-4">
            <summary className="cursor-pointer font-bold text-neutral-950">
              Chi tiết nâng cao
            </summary>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-neutral-500">Sự kiện hợp đồng</dt>
                <dd className="font-mono text-xs">ProofRecorded</dd>
              </div>
              <div>
                <dt className="text-neutral-500">
                  Địa chỉ sổ đăng ký công khai
                </dt>
                <dd className="break-all font-mono text-xs">
                  {preparedIntent?.contractAddress ??
                    "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F"}
                </dd>
              </div>
              <div>
                <dt className="text-neutral-500">Mã hồ sơ trên sổ công khai</dt>
                <dd className="break-all font-mono text-xs">
                  {preparedIntent?.assetId ?? "Tạo khi chuẩn bị giao dịch"}
                </dd>
              </div>
              <div>
                <dt className="text-neutral-500">Ví thực hiện</dt>
                <dd className="break-all font-mono text-xs">
                  {connected?.address ??
                    wallet.data?.walletAddress ??
                    "Chưa kết nối"}
                </dd>
              </div>
            </dl>
          </details>
          <div className="blockchain-signing-action mt-7">
            <button
              className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary-700 px-5 text-sm font-bold text-white disabled:opacity-60 sm:w-auto"
              disabled={
                busy === "sign" ||
                !connected ||
                isWrongWallet ||
                isWrongNetwork ||
                displayedSelected.status === "CONFIRMED"
              }
              onClick={() => void handleSign()}
              type="button"
            >
              {busy === "sign" ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <FileCheck2 className="size-4" />
              )}
              Ký và ghi nhận blockchain
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
