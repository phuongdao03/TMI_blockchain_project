"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Circle,
  FileCheck2,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  proofRegistrySigningApi,
  walletLinkApi,
} from "@/lib/api/client";
import type { THVProofRegistryQueueItem } from "@/lib/api/types";
import {
  connectWallet,
  connectWalletWithConnector,
  hasInjectedMetaMask,
  currentWallet,
  sendTransaction,
  signWalletChallenge,
  subscribeWalletChanges,
  switchChain,
  walletOptions,
  walletAddressesMatch,
  walletErrorCode,
} from "@/lib/blockchain/eip1193";
import {
  clearPendingProofBroadcast,
  readPendingProofBroadcast,
  savePendingProofBroadcast,
  type PendingProofBroadcast,
} from "@/lib/blockchain/pending-proof-broadcast";

type ConnectedWallet = { address: string; chainId: number } | null;

const statusLabel: Record<string, string> = {
  CREATED: "Chờ xác nhận",
  SIGNING: "Đang chờ xác nhận",
  BROADCAST: "Đang xử lý",
  CONFIRMED: "Đã ghi nhận",
  FAILED: "Cần xử lý lại",
  REPLACED: "Đã được thay thế",
};
const terminalStatuses = new Set(["CONFIRMED", "FAILED", "REPLACED"]);
function signingStatusLabel(status: string, transactionHash?: string | null) {
  return status === "FAILED" && transactionHash
    ? "Cần kiểm tra trạng thái"
    : (statusLabel[status] ?? status);
}
const signingSteps = [
  "Chuẩn bị",
  "Chờ xác nhận",
  "Đang xác nhận",
  "Đã ghi nhận",
] as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function errorMessage(
  error: unknown,
  action: "connect" | "verify" | "transaction" = "transaction",
) {
  const walletError = error as { code?: number | string; message?: string };
  const providerCode = walletErrorCode(error);
  if (providerCode === "NO_WALLET") {
    return "Chưa tìm thấy ứng dụng xác nhận. Hãy mở hoặc kết nối ứng dụng đã được tổ chức cấp quyền.";
  }
  if (providerCode === "REQUEST_PENDING") {
    return "Ứng dụng xác nhận đang có yêu cầu chưa xử lý. Hãy mở ứng dụng để hoàn tất hoặc hủy yêu cầu đó.";
  }
  if (providerCode === "UNAUTHORIZED") {
    return "Ứng dụng chưa cho phép kết nối với trang này. Hãy kết nối lại trong ứng dụng.";
  }
  if (providerCode === "DISCONNECTED" || providerCode === "CHAIN_UNAVAILABLE") {
    return "Ứng dụng xác nhận đã ngắt kết nối. Hãy mở ứng dụng và thử kết nối lại.";
  }
  if (providerCode === "USER_REJECTED") {
    if (action === "connect")
      return "Bạn chưa chấp thuận kết nối. Hãy chọn Kết nối để thử lại.";
    if (action === "verify")
      return "Bạn chưa chấp thuận bước kiểm tra quyền. Chưa có thay đổi nào được ghi nhận.";
    return "Bạn chưa chấp thuận xác nhận. Chưa có thay đổi nào được ghi nhận.";
  }
  if (action === "verify" && error instanceof ApiError) {
    if (error.status === 403)
      return "Ứng dụng xác nhận chưa được cấp quyền cho thao tác này. Hãy liên hệ quản trị viên.";
    if (error.status === 503)
      return "Chưa thể kiểm tra quyền xác nhận lúc này. Hãy thử lại sau.";
  }
  if (
    walletError?.code === -32000 ||
    walletError?.message?.toLowerCase().includes("insufficient funds")
  ) {
    return "Chưa thể hoàn tất xác nhận. Hãy liên hệ bộ phận hỗ trợ để được kiểm tra.";
  }
  if (action === "connect")
    return "Chưa thể kết nối ứng dụng xác nhận. Hãy kiểm tra ứng dụng và thử lại.";
  if (action === "verify")
    return "Chưa thể kiểm tra quyền xác nhận. Hãy kiểm tra ứng dụng và thử lại.";
  return "Chưa thể hoàn tất thao tác. Vui lòng thử lại hoặc liên hệ bộ phận vận hành.";
}

function signingStep(
  status: string,
  busy: "connect" | "link" | "sign" | null,
  transactionHash?: string | null,
) {
  if (status === "CONFIRMED") return 3;
  if (
    status === "BROADCAST" ||
    (status === "FAILED" && Boolean(transactionHash)) ||
    (status === "SIGNING" && transactionHash)
  ) {
    return 2;
  }
  if (status === "SIGNING" || busy === "sign") return 1;
  return 0;
}

function verificationMessage(
  status: string,
  transactionHash?: string | null,
  errorCode?: string | null,
) {
  if (status === "CONFIRMED") {
    return "Tài liệu đã được ghi nhận và chưa bị thay đổi.";
  }
  if (status === "BROADCAST") {
    return "Yêu cầu đang được xử lý. Trạng thái sẽ cập nhật sau khi hoàn tất.";
  }
  if (status === "SIGNING") {
    if (transactionHash) {
      return "Đã nhận yêu cầu xác nhận. Hệ thống đang cập nhật trạng thái.";
    }
    return "Chưa nhận được xác nhận. Bạn có thể mở lại ứng dụng để tiếp tục.";
  }
  if (status === "FAILED") {
    if (transactionHash) {
      if (errorCode === "TRANSACTION_REVERTED") {
        return "Chưa hoàn tất việc ghi nhận. Hãy kiểm tra lại trạng thái trước khi thử lại.";
      }
      return "Hồ sơ đang được kiểm tra. Hãy chọn “Kiểm tra trạng thái” trước khi thao tác lại.";
    }
    return "Chưa ghi nhận được hồ sơ. Vui lòng kiểm tra thông tin và thử lại.";
  }
  return "Hồ sơ đã sẵn sàng. Hãy kiểm tra thông tin trước khi xác nhận.";
}

export function BlockchainSigningWorkspace() {
  const queryClient = useQueryClient();
  const signingInFlight = useRef(false);
  const [connected, setConnected] = useState<ConnectedWallet>(null);
  const [selected, setSelected] = useState<THVProofRegistryQueueItem | null>(
    null,
  );
  const [pendingBroadcast, setPendingBroadcast] =
    useState<PendingProofBroadcast | null>(null);
  const [busy, setBusy] = useState<"connect" | "link" | "sign" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(
    null,
  );
  const [walletPickerOpen, setWalletPickerOpen] = useState(false);
  const [pollStartedAt, setPollStartedAt] = useState(() => Date.now());

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
      selected?.transactionId &&
        (!terminalStatuses.has(selected.status) ||
          (selected.status === "FAILED" && selected.txHash)),
    ),
    retry: false,
    refetchInterval: (query) => {
      if (Date.now() - pollStartedAt >= 5 * 60_000) return false;
      if (
        query.state.data &&
        terminalStatuses.has(query.state.data.status) &&
        !(query.state.data.status === "FAILED" && query.state.data.txHash)
      ) {
        return false;
      }
      return query.state.error || query.state.data?.status === "FAILED"
        ? 15_000
        : 4_000;
    },
    refetchIntervalInBackground: false,
  });

  const displayedSelected =
    selected && transactionStatus.data?.transactionId === selected.transactionId
      ? {
          ...selected,
          status:
            (transactionStatus.data.txHash ?? selected.txHash) &&
            ["CREATED", "SIGNING"].includes(transactionStatus.data.status)
              ? "BROADCAST"
              : transactionStatus.data.status,
          txHash: transactionStatus.data.txHash ?? selected.txHash,
          confirmations: transactionStatus.data.confirmations,
          errorCode: transactionStatus.data.errorCode,
        }
      : selected;
  const confirmationUnavailable =
    transactionStatus.error instanceof ApiError &&
    transactionStatus.error.status === 503;

  useEffect(() => {
    const next = transactionStatus.data;
    if (!next) return;
    if (
      terminalStatuses.has(next.status) &&
      !(next.status === "FAILED" && next.txHash)
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["blockchain", "proof-registry", "signing-queue"],
      });
    }
  }, [queryClient, transactionStatus.data]);

  const refreshWalletState = useCallback(async () => {
    try {
      const next = await currentWallet();
      const available = next.address
        ? { address: next.address, chainId: next.chainId }
        : null;
      setConnected(available);
      if (next.address) setConnectionError(null);
      return available;
    } catch {
      setConnected(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void refreshWalletState();
    });
    return () => {
      active = false;
    };
  }, [refreshWalletState]);

  useEffect(() => {
    const refreshAfterWallet = () => {
      void refreshWalletState();
      if (selected?.transactionId) {
        void queryClient.invalidateQueries({
          queryKey: [
            "blockchain",
            "proof-registry",
            "transaction",
            selected.transactionId,
          ],
        });
      }
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refreshAfterWallet();
    };
    window.addEventListener("focus", refreshAfterWallet);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refreshAfterWallet);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [queryClient, refreshWalletState, selected?.transactionId]);

  useEffect(() => {
    try {
      return subscribeWalletChanges(() => {
        setMessage(
          "Trạng thái kết nối đã thay đổi. Vui lòng kiểm tra lại trước khi xác nhận.",
        );
        void refreshWalletState();
        void queryClient.invalidateQueries({ queryKey: ["blockchain"] });
      });
    } catch {
      return undefined;
    }
  }, [connected?.address, queryClient, refreshWalletState]);

  async function handleConnect() {
    setBusy("connect");
    setMessage(null);
    setConnectionError(null);
    setVerificationError(null);
    const options = walletOptions?.() ?? [];
    if (options.length > 1 && !hasInjectedMetaMask()) {
      setBusy(null);
      setWalletPickerOpen(true);
      return;
    }
    try {
      setConnected(await connectWallet());
    } catch (error) {
      if (!(await refreshWalletState()))
        setConnectionError(errorMessage(error, "connect"));
    } finally {
      setBusy(null);
    }
  }

  async function handleConnectWithConnector(connectorId: string) {
    setBusy("connect");
    setMessage(null);
    setConnectionError(null);
    setVerificationError(null);
    try {
      setConnected(await connectWalletWithConnector(connectorId));
      setWalletPickerOpen(false);
    } catch (error) {
      if (!(await refreshWalletState()))
        setConnectionError(errorMessage(error, "connect"));
      setWalletPickerOpen(false);
    } finally {
      setBusy(null);
    }
  }

  async function handleVerifyWallet() {
    if (!connected) return;
    if (
      wallet.data &&
      !walletAddressesMatch(wallet.data.walletAddress, connected.address)
    ) {
      setMessage("Ứng dụng hiện tại chưa được xác minh cho thao tác này.");
      return;
    }
    setBusy("link");
    setMessage(null);
    setVerificationError(null);
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
      setMessage(
        wallet.data
          ? "Đã kiểm tra quyền xác nhận thành công. Chưa có thay đổi nào được ghi nhận."
          : "Quyền xác nhận của tổ chức đã được kiểm tra và sẵn sàng sử dụng.",
      );
    } catch (error) {
      setVerificationError(errorMessage(error, "verify"));
    } finally {
      setBusy(null);
    }
  }

  function openItem(item: THVProofRegistryQueueItem) {
    setPollStartedAt(() => Date.now());
    const pending = !item.txHash
      ? readPendingProofBroadcast(item.dossierId, item.version)
      : null;
    setPendingBroadcast(pending);
    setSelected(
      pending
        ? {
            ...item,
            transactionId: pending.transactionId,
            status: "BROADCAST",
            txHash: pending.transactionHash,
          }
        : item.txHash && ["CREATED", "SIGNING"].includes(item.status)
          ? { ...item, status: "BROADCAST" }
          : item,
    );
    setMessage(null);
  }

  async function handleSign() {
    if (!selected || !connected || selected.txHash || signingInFlight.current)
      return;
    if (readPendingProofBroadcast(selected.dossierId, selected.version)) {
      setMessage(
        "Yêu cầu xác nhận đã được gửi. Hãy kiểm tra trạng thái trước khi thao tác lại.",
      );
      return;
    }
    if (
      !wallet.data ||
      !walletAddressesMatch(wallet.data.walletAddress, connected.address)
    ) {
      setMessage("Hãy kết nối ứng dụng đã được xác minh trước khi xác nhận.");
      return;
    }
    if (connected.chainId !== wallet.data.chainId) {
      setMessage(
        "Ứng dụng xác nhận chưa sẵn sàng. Hãy kiểm tra kết nối rồi thử lại.",
      );
      return;
    }
    signingInFlight.current = true;
    setBusy("sign");
    setMessage(null);
    let transactionHash: string | null = null;
    try {
      const intent = await proofRegistrySigningApi.prepareIntent(
        selected.dossierId,
        selected.version,
        connected.address,
      );
      transactionHash = await sendTransaction({
        ...intent.transactionRequest,
        from: connected.address,
      });
      setPollStartedAt(Date.now());
      const pending = {
        dossierId: selected.dossierId,
        version: selected.version,
        transactionId: intent.transactionId,
        intentId: intent.intentId,
        transactionHash,
        connectedWallet: connected.address,
      };
      savePendingProofBroadcast(pending);
      setPendingBroadcast(pending);
      setSelected((current) =>
        current
          ? {
              ...current,
              transactionId: intent.transactionId,
              status: "BROADCAST",
              txHash: transactionHash,
              confirmations: 0,
              errorCode: null,
            }
          : current,
      );
      setMessage("Yêu cầu đã được gửi. Hệ thống đang cập nhật trạng thái.");
      const submitted = await proofRegistrySigningApi.submitTransaction({
        transactionId: intent.transactionId,
        intentId: intent.intentId,
        transactionHash,
        connectedWallet: connected.address,
      });
      clearPendingProofBroadcast(pending);
      setPendingBroadcast(null);
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
      setMessage("Yêu cầu đã được gửi. Hệ thống sẽ cập nhật khi hoàn tất.");
      await queryClient.invalidateQueries({
        queryKey: ["blockchain", "proof-registry", "signing-queue"],
      });
    } catch (error) {
      if (
        !transactionHash &&
        error instanceof ApiError &&
        error.status === 409 &&
        selected.transactionId
      ) {
        try {
          const recovered = await proofRegistrySigningApi.status(
            selected.transactionId,
          );
          setSelected((current) =>
            current
              ? {
                  ...current,
                  transactionId: recovered.transactionId,
                  status: recovered.status,
                  txHash: recovered.txHash,
                  confirmations: recovered.confirmations,
                  errorCode: recovered.errorCode,
                }
              : current,
          );
          queryClient.setQueryData(
            [
              "blockchain",
              "proof-registry",
              "transaction",
              selected.transactionId,
            ],
            recovered,
          );
          setMessage(
            recovered.status === "CONFIRMED"
              ? "Hồ sơ đã được ghi nhận. Bạn không cần xác nhận lại."
              : "Đã tìm thấy yêu cầu trước đó. Hệ thống đang kiểm tra trạng thái; bạn không cần xác nhận lại.",
          );
          await queryClient.invalidateQueries({
            queryKey: ["blockchain", "proof-registry", "signing-queue"],
          });
          return;
        } catch {
          setMessage(
            "Yêu cầu có thể đã được gửi trước đó. Hãy chọn “Kiểm tra trạng thái”; không thao tác lại khi chưa kiểm tra.",
          );
          return;
        }
      }
      setMessage(
        transactionHash
          ? "Yêu cầu đã được gửi. Hệ thống sẽ tiếp tục cập nhật trạng thái; không cần thao tác lại."
          : errorMessage(error),
      );
    } finally {
      signingInFlight.current = false;
      setBusy(null);
    }
  }

  const resumePendingBroadcast = useCallback(
    async (pending: PendingProofBroadcast) => {
      if (
        !connected ||
        !wallet.data ||
        !walletAddressesMatch(
          wallet.data.walletAddress,
          pending.connectedWallet,
        ) ||
        !walletAddressesMatch(connected.address, pending.connectedWallet) ||
        signingInFlight.current
      ) {
        return;
      }
      signingInFlight.current = true;
      setBusy("sign");
      try {
        const submitted = await proofRegistrySigningApi.submitTransaction({
          transactionId: pending.transactionId,
          intentId: pending.intentId,
          transactionHash: pending.transactionHash,
          connectedWallet: pending.connectedWallet,
        });
        clearPendingProofBroadcast(pending);
        setPendingBroadcast(null);
        setSelected((current) =>
          current?.dossierId === pending.dossierId &&
          current.version === pending.version
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
          "Đã nhận yêu cầu xác nhận. Hệ thống đang cập nhật trạng thái.",
        );
        await queryClient.invalidateQueries({
          queryKey: ["blockchain", "proof-registry", "signing-queue"],
        });
      } catch {
        try {
          const status = await proofRegistrySigningApi.status(
            pending.transactionId,
          );
          if (
            status.txHash?.toLowerCase() ===
              pending.transactionHash.toLowerCase() ||
            status.status === "CONFIRMED"
          ) {
            clearPendingProofBroadcast(pending);
            setPendingBroadcast(null);
            setSelected((current) =>
              current?.dossierId === pending.dossierId &&
              current.version === pending.version
                ? {
                    ...current,
                    transactionId: status.transactionId,
                    status: status.status,
                    txHash: status.txHash,
                    confirmations: status.confirmations,
                    errorCode: status.errorCode,
                  }
                : current,
            );
            setMessage("Hồ sơ đã được ghi nhận. Bạn không cần xác nhận lại.");
            return;
          }
        } catch {
          // Keep the local hash so a retry never starts another wallet prompt.
        }
        setMessage(
          "Chưa thể cập nhật trạng thái. Yêu cầu đã được gửi; hãy thử lại khi có kết nối.",
        );
      } finally {
        signingInFlight.current = false;
        setBusy(null);
      }
    },
    [connected, queryClient, wallet.data],
  );

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active && pendingBroadcast)
        void resumePendingBroadcast(pendingBroadcast);
    });
    return () => {
      active = false;
    };
  }, [pendingBroadcast, resumePendingBroadcast]);

  const requiredChain = wallet.data?.chainId ?? 137;
  const isWrongNetwork = Boolean(
    connected && requiredChain && connected.chainId !== requiredChain,
  );
  const isWrongWallet = Boolean(
    connected &&
      wallet.data &&
      !walletAddressesMatch(connected.address, wallet.data.walletAddress),
  );
  const notice = connectionError ?? verificationError ?? message;
  const noticeIsError = Boolean(connectionError || verificationError);

  if (wallet.isPending)
    return (
      <section
        className="blockchain-surface mx-auto flex max-w-3xl items-center gap-4 rounded-2xl border p-6"
        role="status"
      >
        <LoaderCircle
          className="auth-activity-spinner size-6 text-primary-700"
          aria-hidden="true"
        />
        <div>
          <p className="font-bold">Đang kiểm tra quyền ký</p>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            Đang tải hồ sơ đủ điều kiện ghi nhận…
          </p>
        </div>
      </section>
    );
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
      <header className="blockchain-signing-hero rounded-3xl bg-neutral-950 px-7 py-8 text-white sm:px-10 sm:py-10">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary-300">
          Ghi nhận hồ sơ đã phê duyệt
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Hồ sơ chờ ghi nhận
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              Chọn hồ sơ đã hoàn tất thẩm định và đủ điều kiện thu phí hoặc miễn
              phí để xác nhận ghi nhận. Bản ghi giúp đối chiếu hồ sơ và phiên
              bản; tài liệu gốc và dữ liệu cá nhân vẫn được bảo vệ trong hồ sơ.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {connected ? (
              <span className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-white/30 px-3 text-sm font-semibold text-white">
                <CheckCircle2 className="size-4" aria-hidden="true" />
                Ứng dụng xác nhận đã kết nối
              </span>
            ) : null}
            <button
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-white px-4 text-sm font-bold text-neutral-950 hover:bg-neutral-100 disabled:opacity-60"
              disabled={busy === "connect"}
              onClick={() => void handleConnect()}
              type="button"
            >
              {busy === "connect" ? (
                <LoaderCircle
                  className="auth-activity-spinner size-4"
                  aria-hidden="true"
                />
              ) : (
                <WalletCards className="size-4" aria-hidden="true" />
              )}
              {connected ? "Làm mới kết nối" : "Kết nối ứng dụng xác nhận"}
            </button>
          </div>
        </div>
      </header>

      {notice ? (
        <div
          className={`flex items-start gap-3 rounded-xl border px-5 py-4 text-sm leading-6 ${noticeIsError ? "border-amber-300 bg-amber-50 text-amber-950" : "border-primary-200 bg-primary-50 text-primary-950"}`}
          role={noticeIsError ? "alert" : "status"}
          aria-live="polite"
        >
          {busy ? (
            <LoaderCircle
              className="auth-activity-spinner mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
          ) : noticeIsError ? (
            <AlertTriangle
              className="mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <CheckCircle2
              className="mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
          )}
          <p>{notice}</p>
        </div>
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
                  Chọn ứng dụng xác nhận
                </h2>
                <p className="mt-1 text-sm text-neutral-600">
                  Chọn ứng dụng đã được tổ chức cấp quyền cho tài khoản này.
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
              {walletOptions().map((option, index) => (
                <button
                  key={option.id}
                  type="button"
                  className="flex min-h-12 items-center gap-3 rounded-xl border px-4 text-left font-semibold transition-colors hover:bg-neutral-100 disabled:opacity-60"
                  disabled={busy === "connect"}
                  onClick={() => void handleConnectWithConnector(option.id)}
                >
                  <WalletCards className="size-5" aria-hidden="true" />
                  <span>Ứng dụng xác nhận {index + 1}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <section>
        <article className="blockchain-wallet-panel blockchain-surface rounded-2xl border p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
                Quyền xác nhận của tổ chức
              </p>
              <h2 className="mt-2 text-xl font-bold text-neutral-950">
                {wallet.data ? "Đã xác minh quyền" : "Chưa xác minh quyền"}
              </h2>
            </div>
            <ShieldCheck
              className="size-6 text-primary-700"
              aria-hidden="true"
            />
          </div>
          <p className="mt-4 text-sm text-neutral-600">
            Chỉ tài khoản được tổ chức cấp quyền mới có thể xác nhận ghi nhận hồ
            sơ.
          </p>
          {isWrongWallet || isWrongNetwork ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <div className="flex gap-2 font-bold">
                <AlertTriangle className="size-4" aria-hidden="true" />
                Ứng dụng xác nhận chưa sẵn sàng
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
                  Kiểm tra kết nối
                </button>
              ) : null}
            </div>
          ) : null}
          {connected && !isWrongWallet && !isWrongNetwork ? (
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white disabled:opacity-60"
                disabled={busy === "link"}
                onClick={() => void handleVerifyWallet()}
                type="button"
              >
                {busy === "link" ? (
                  <LoaderCircle className="auth-activity-spinner size-4" />
                ) : (
                  <BadgeCheck className="size-4" />
                )}
                {wallet.data
                  ? "Kiểm tra quyền xác nhận"
                  : "Xác minh quyền của tổ chức"}
              </button>
              {wallet.data ? (
                <p className="text-sm text-neutral-600">
                  Bước kiểm tra không ghi nhận hồ sơ và không làm thay đổi nội
                  dung.
                </p>
              ) : null}
            </div>
          ) : null}
        </article>
      </section>

      <section className="blockchain-queue-panel blockchain-surface rounded-2xl border">
        <div className="flex items-center justify-between gap-4 border-b border-[var(--theme-border)] px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
              Hồ sơ đủ điều kiện ghi nhận
            </p>
            <h2 className="mt-1 text-xl font-bold text-neutral-950">
              Hồ sơ chờ ghi nhận
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
            Kết nối ứng dụng xác nhận để xem hồ sơ đủ điều kiện.
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
            Không có hồ sơ đủ điều kiện đang chờ ghi nhận.
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
              <span className="blockchain-status-pill rounded-full px-3 py-1.5 text-xs font-bold">
                {signingStatusLabel(item.status, item.txHash)}
              </span>
            </button>
          ))}
        </div>
      </section>

      {displayedSelected ? (
        <section className="blockchain-signing-panel blockchain-surface rounded-2xl border p-6 sm:p-8">
          <div className="blockchain-signing-heading flex items-start justify-between gap-5">
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
            <span className="blockchain-status-pill rounded-full px-3 py-1.5 text-xs font-bold">
              {signingStatusLabel(
                displayedSelected.status,
                displayedSelected.txHash,
              )}
            </span>
          </div>
          <ol
            aria-label="Tiến trình ký"
            className="blockchain-signing-steps mt-7 grid gap-2 sm:grid-cols-4"
          >
            {signingSteps.map((step, index) => {
              const currentStep = signingStep(
                displayedSelected.status,
                busy,
                displayedSelected.txHash,
              );
              const complete = index < currentStep || currentStep === 3;
              const current = index === currentStep;
              return (
                <li
                  aria-current={current ? "step" : undefined}
                  data-complete={complete ? "true" : undefined}
                  className={`flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2 text-xs font-bold transition-[background-color,border-color,color] duration-150 ${
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
                  ) : current && displayedSelected.status === "FAILED" ? (
                    <AlertTriangle
                      className="size-4 shrink-0"
                      aria-hidden="true"
                    />
                  ) : (
                    <Circle className="size-4 shrink-0" aria-hidden="true" />
                  )}
                  {index === 2 && displayedSelected.status === "FAILED"
                    ? "Cần kiểm tra"
                    : step}
                </li>
              );
            })}
          </ol>

          <div
            className="blockchain-soft-surface mt-5 rounded-xl border p-4"
            role="status"
          >
            <p className="font-bold text-neutral-950">
              {verificationMessage(
                displayedSelected.status,
                displayedSelected.txHash,
                displayedSelected.errorCode,
              )}
            </p>
            {(displayedSelected.status === "BROADCAST" ||
              (displayedSelected.status === "SIGNING" &&
                displayedSelected.txHash)) &&
            !transactionStatus.error ? (
              <p className="mt-1 text-sm text-neutral-600">
                Hệ thống đối soát kết quả; bạn có thể kiểm tra lại bất kỳ lúc
                nào. Trạng thái sẽ chuyển thành “Đã ghi nhận” sau khi hoàn tất.
              </p>
            ) : null}
          </div>

          {displayedSelected.status === "CONFIRMED" ? (
            <section className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-5 text-neutral-950">
              <div className="flex items-center gap-3">
                <ShieldCheck
                  className="size-6 shrink-0 text-emerald-700"
                  aria-hidden="true"
                />
                <div>
                  <h3 className="font-bold">Hồ sơ đã được ghi nhận</h3>
                  {transactionStatus.data?.confirmedAt ? (
                    <p className="mt-1 text-sm text-neutral-600">
                      Ghi nhận lúc{" "}
                      {formatDate(transactionStatus.data.confirmedAt)}.
                    </p>
                  ) : null}
                </div>
              </div>
              <p className="mt-4 text-xs leading-5 text-neutral-600">
                Bản ghi giúp đối chiếu mã hồ sơ và phiên bản đã xác nhận; không
                lưu tệp gốc hoặc tài liệu cá nhân.
              </p>
            </section>
          ) : null}

          {transactionStatus.error ? (
            <div
              className="blockchain-confirmation-warning mt-4 rounded-xl border p-4"
              role="alert"
            >
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className="mt-0.5 size-5 shrink-0"
                  aria-hidden="true"
                />
                <div>
                  <h3 className="font-bold">
                    {confirmationUnavailable
                      ? "Chưa nhận được kết quả xác nhận"
                      : "Chưa cập nhật được trạng thái"}
                  </h3>
                  <p className="mt-1 text-sm leading-6">
                    Yêu cầu vẫn đang được giữ an toàn. Hệ thống sẽ tự kiểm tra
                    lại; bạn cũng có thể kiểm tra ngay mà không cần xác nhận
                    lại.
                  </p>
                  <button
                    className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg border px-3 text-sm font-bold"
                    disabled={transactionStatus.isFetching}
                    onClick={() => void transactionStatus.refetch()}
                    type="button"
                  >
                    <RefreshCw
                      className={`size-4 ${transactionStatus.isFetching ? "auth-activity-spinner" : ""}`}
                      aria-hidden="true"
                    />
                    {transactionStatus.isFetching
                      ? "Đang kiểm tra…"
                      : "Thử kiểm tra lại"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <dl className="blockchain-signing-metadata mt-5 grid gap-3 sm:grid-cols-2">
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Mã hồ sơ</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {displayedSelected.dossierCode}
              </dd>
            </div>
            <div className="blockchain-soft-surface rounded-xl p-4">
              <dt className="text-xs text-neutral-500">Phiên bản</dt>
              <dd className="mt-2 font-bold text-neutral-950">
                {displayedSelected.version}
              </dd>
            </div>
          </dl>
          <div className="blockchain-signing-action mt-7">
            {displayedSelected.status === "BROADCAST" ||
            (displayedSelected.status === "FAILED" &&
              displayedSelected.txHash) ||
            (displayedSelected.status === "SIGNING" &&
              displayedSelected.txHash) ? (
              <button
                className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-5 text-sm font-bold text-[var(--theme-text)] disabled:opacity-60 sm:w-auto"
                disabled={transactionStatus.isFetching || busy === "sign"}
                onClick={() =>
                  pendingBroadcast
                    ? void resumePendingBroadcast(pendingBroadcast)
                    : void transactionStatus.refetch()
                }
                type="button"
              >
                <RefreshCw
                  className={`size-4 ${transactionStatus.isFetching ? "auth-activity-spinner" : ""}`}
                />
                {busy === "sign" && pendingBroadcast
                  ? "Đang kiểm tra trạng thái…"
                  : pendingBroadcast
                    ? "Tiếp tục kiểm tra"
                    : transactionStatus.isFetching
                      ? "Đang kiểm tra trạng thái…"
                      : "Kiểm tra trạng thái"}
              </button>
            ) : null}
            {!displayedSelected.txHash &&
            !["BROADCAST", "CONFIRMED", "REPLACED"].includes(
              displayedSelected.status,
            ) ? (
              <button
                className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary-700 px-5 text-sm font-bold text-white disabled:opacity-60 sm:w-auto"
                disabled={
                  busy === "sign" ||
                  !connected ||
                  isWrongWallet ||
                  isWrongNetwork
                }
                onClick={() => void handleSign()}
                type="button"
              >
                <FileCheck2 className="size-4" />
                {busy === "sign"
                  ? "Đang chờ xác nhận…"
                  : displayedSelected.status === "SIGNING"
                    ? "Mở lại ứng dụng để tiếp tục"
                    : "Xác nhận ghi nhận hồ sơ"}
              </button>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
