"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  FileCheck2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  blockchainSigningApi,
  proofRegistrySigningApi,
} from "@/lib/api/client";
import type {
  THVProofRegistryIntent,
  THVProofRegistryQueueItem,
} from "@/lib/api/types";
import {
  connectWallet,
  currentWallet,
  sendTransaction,
  signWalletChallenge,
  subscribeWalletChanges,
  switchChain,
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
  return error instanceof ApiError || error instanceof Error
    ? error.message
    : "Không thể hoàn tất thao tác. Vui lòng thử lại.";
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

  const wallet = useQuery({
    queryKey: ["blockchain", "wallet"],
    queryFn: blockchainSigningApi.currentWallet,
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
    try {
      setConnected(await connectWallet());
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
      const challenge = await blockchainSigningApi.issueWalletChallenge(
        connected.address,
        connected.chainId,
      );
      const signature = await signWalletChallenge(
        challenge.message,
        connected.address,
      );
      await blockchainSigningApi.verifyWalletLink({
        challengeId: challenge.id,
        nonce: challenge.nonce,
        signature,
      });
      await queryClient.invalidateQueries({ queryKey: ["blockchain"] });
      setMessage("Ví đã được xác minh và sẵn sàng ký bằng VERIFIER_ROLE.");
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
        "Giao dịch đã được gửi. Hệ thống đang kiểm tra receipt, sự kiện ProofRecorded và số xác nhận.",
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
    return <p role="status">Đang kiểm tra quyền ký blockchain…</p>;
  if (wallet.error) {
    const apiError = wallet.error instanceof ApiError ? wallet.error : null;
    const isForbidden = apiError?.status === 403;
    const title = isForbidden
      ? "Chưa có quyền ký blockchain"
      : "Dịch vụ blockchain chưa sẵn sàng";
    const description = isForbidden
      ? "Phiên đăng nhập hiện tại chưa có quyền blockchain.sign. Hãy đăng xuất, đăng nhập lại và kiểm tra quyền của tài khoản Super Admin."
      : "Tài khoản đã vào được khu vực quản trị, nhưng backend chưa tải được cấu hình hoặc dịch vụ blockchain. Kiểm tra RPC, chain ID, contract, allowlist và ABI trên production.";
    return (
      <section className="blockchain-error-state mx-auto max-w-3xl rounded-2xl border p-7">
        <ShieldCheck className="size-6" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-bold">{title}</h1>
        <p className="mt-2 leading-7">{description}</p>
        <p className="mt-4 font-mono text-xs font-bold uppercase tracking-[0.12em]">
          Mã lỗi: {apiError?.code ?? "REQUEST_FAILED"}
        </p>
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
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="rounded-3xl bg-neutral-950 px-7 py-8 text-white sm:px-10 sm:py-10">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary-300">
          THVProofRegistry
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-5xl">
              Hàng đợi chờ ký
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              Hồ sơ chỉ xuất hiện sau khi kiểm duyệt hoàn tất. Ví của Super
              Admin xác nhận recordProof; file và dữ liệu cá nhân không lên
              blockchain.
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

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <article className="rounded-2xl border border-neutral-200 bg-white p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
                Ví VERIFIER_ROLE
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
            <div className="rounded-xl bg-neutral-50 p-4">
              <dt className="text-neutral-500">Mạng yêu cầu</dt>
              <dd className="mt-1 font-bold text-neutral-950">
                Chain ID {requiredChain ?? "–"}
              </dd>
            </div>
            <div className="rounded-xl bg-neutral-50 p-4">
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
                  Chuyển sang Chain ID {requiredChain}
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
              Ký xác minh quyền sở hữu ví
            </button>
          ) : null}
        </article>

        <article className="rounded-2xl border border-neutral-200 bg-[#f8f8f4] p-6">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Kiểm soát an toàn
          </p>
          <ul className="mt-4 space-y-4 text-sm leading-6 text-neutral-700">
            <li className="flex gap-3">
              <CheckCircle2 className="mt-0.5 size-4 text-primary-700" />
              THV không yêu cầu private key hoặc seed phrase.
            </li>
            <li className="flex gap-3">
              <CheckCircle2 className="mt-0.5 size-4 text-primary-700" />
              Backend đối chiếu sender, chain, contract, calldata và proof hash.
            </li>
            <li className="flex gap-3">
              <CheckCircle2 className="mt-0.5 size-4 text-primary-700" />
              Chỉ CONFIRMED sau receipt, ProofRecorded và đọc lại contract.
            </li>
          </ul>
        </article>
      </section>

      <section className="rounded-2xl border border-neutral-200 bg-white">
        <div className="flex items-center justify-between gap-4 border-b border-neutral-200 px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
              Proof đã khóa
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
              className="grid w-full gap-3 px-6 py-5 text-left transition hover:bg-neutral-50 md:grid-cols-[1fr_auto] md:items-center"
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
                  recordProof · tạo {formatDate(item.createdAt)}
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
        <section className="rounded-2xl border border-neutral-200 bg-white p-6 sm:p-8">
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
                {displayedSelected.version} · recordProof
              </p>
            </div>
            <span className="rounded-full bg-neutral-100 px-3 py-1.5 text-xs font-bold text-neutral-700">
              {statusLabel[displayedSelected.status] ??
                displayedSelected.status}
            </span>
          </div>
          <dl className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl bg-neutral-50 p-4 xl:col-span-2">
              <dt className="text-xs text-neutral-500">Proof SHA-256</dt>
              <dd className="mt-2 break-all font-mono text-xs text-neutral-900">
                {displayedSelected.proofHash}
              </dd>
            </div>
            <div className="rounded-xl bg-neutral-50 p-4">
              <dt className="text-xs text-neutral-500">Xác nhận</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {displayedSelected.confirmations}
              </dd>
            </div>
            <div className="rounded-xl bg-neutral-50 p-4">
              <dt className="text-xs text-neutral-500">Contract</dt>
              <dd className="mt-2 break-all font-mono text-xs text-neutral-900">
                {preparedIntent?.contractAddress ?? "Xác định khi tạo intent"}
              </dd>
            </div>
          </dl>
          {displayedSelected.txHash ? (
            <p className="mt-4 break-all font-mono text-xs text-neutral-600">
              Tx: {displayedSelected.txHash}
            </p>
          ) : null}
          <button
            className="mt-7 inline-flex min-h-12 items-center gap-2 rounded-lg bg-primary-700 px-5 text-sm font-bold text-white disabled:opacity-60"
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
            Ký & ghi nhận blockchain
          </button>
        </section>
      ) : null}
    </div>
  );
}
