import type { DossierStatus, DossierTimelineItem } from "@/lib/api/types";

export type ProgressInput = {
  status: DossierStatus;
  history: readonly Pick<
    DossierTimelineItem,
    "fromStatus" | "toStatus" | "createdAt" | "note"
  >[];
  submissionFeePolicyMode?: string;
  submissionFeeTestExempted?: boolean;
  submissionFeeRequired?: boolean;
  submissionFeePaidAt?: string | null;
  submissionFeeWaivedAt?: string | null;
  isTest?: boolean;
};
type Stage = { key: string; label: string; statuses: DossierStatus[] };
export function dossierProgress(input: ProgressInput) {
  const { status, submissionFeePaidAt, submissionFeeWaivedAt } = input;
  const history = [...input.history].sort((a, b) =>
    a.createdAt.localeCompare(b.createdAt),
  );
  const reviewEvent = history.find((item) =>
    ["UNDER_REVIEW", "COUNCIL_REVIEW", "APPROVED"].includes(item.toStatus),
  );
  const feeEvent = history.find((item) => item.toStatus === "PAYMENT_PENDING");
  const feeTime = submissionFeePaidAt ?? submissionFeeWaivedAt;
  const historicalPostReviewFee = Boolean(
    reviewEvent &&
      ((feeEvent &&
        Date.parse(feeEvent.createdAt) > Date.parse(reviewEvent.createdAt)) ||
        (feeTime && Date.parse(feeTime) > Date.parse(reviewEvent.createdAt))),
  );
  // Actual historical events take precedence over policy metadata.
  const modern =
    !historicalPostReviewFee &&
    Boolean(
      input.submissionFeePolicyMode === "DYNAMIC" ||
        input.submissionFeeRequired ||
        submissionFeePaidAt ||
        submissionFeeWaivedAt,
    );
  const legacyFeePaid =
    !modern &&
    [
      "PAID",
      "ANCHOR_PENDING",
      "ANCHORED",
      "CERTIFICATE_ISSUED",
      "PUBLISHED",
      "REVOKED",
    ].includes(status);
  const preparation: Stage = {
    key: "preparation",
    label: "Chuẩn bị hồ sơ",
    statuses: ["DRAFT"],
  };
  const fee: Stage = {
    key: "fee",
    label: modern ? "Thanh toán phí nộp" : "Hoàn tất lệ phí",
    statuses: ["PAYMENT_PENDING"],
  };
  const intake: Stage = {
    key: "intake",
    label: "Kiểm tra ban đầu",
    statuses: ["SUBMITTED", "PRECHECK"],
  };
  const review: Stage = {
    key: "review",
    label: "Thẩm định",
    statuses: ["UNDER_REVIEW", "COUNCIL_REVIEW"],
  };
  const decision: Stage = {
    key: "decision",
    label: "Quyết định hồ sơ",
    statuses: ["APPROVED", "REJECTED"],
  };
  const certificate: Stage = {
    key: "certificate",
    label: "Hoàn thiện bằng xác lập",
    statuses: ["PAID", "ANCHOR_PENDING", "ANCHORED", "CERTIFICATE_ISSUED"],
  };
  const publication: Stage = {
    key: "publication",
    label: "Công bố",
    statuses: ["PUBLISHED"],
  };
  const definitions = modern
    ? [preparation, fee, intake, review, decision, certificate, publication]
    : [preparation, intake, review, decision, fee, certificate, publication];
  const last = history.at(-1);
  const pausedStatus =
    status === "NEEDS_SUPPLEMENT" ? last?.fromStatus : status;
  const current =
    definitions.find((s) => s.statuses.includes(pausedStatus ?? status)) ??
    intake;
  const stopped = ["REJECTED", "CANCELLED", "REVOKED"].includes(status);
  const stages = definitions.map((stage) => {
    // A transition out of a stage is evidence; the stage index is not.
    const exit = history.find(
      (item) =>
        stage.statuses.includes(item.fromStatus) &&
        !stage.statuses.includes(item.toStatus) &&
        !["NEEDS_SUPPLEMENT", "REJECTED", "CANCELLED", "REVOKED"].includes(
          item.toStatus,
        ),
    );
    const settledAt =
      stage.key === "fee"
        ? (submissionFeePaidAt ?? submissionFeeWaivedAt)
        : null;
    const legacyFeeComplete = stage.key === "fee" && legacyFeePaid;
    const finalEvent =
      stage.key === "publication" && status === "PUBLISHED"
        ? history.find((item) => item.toStatus === "PUBLISHED")
        : null;
    const issued =
      stage.key === "certificate"
        ? history.find((item) => item.toStatus === "CERTIFICATE_ISSUED")
        : null;
    const complete = Boolean(
      exit ||
        settledAt ||
        legacyFeeComplete ||
        finalEvent ||
        issued ||
        (stage.key === "publication" && status === "PUBLISHED"),
    );
    return {
      ...stage,
      state: stopped
        ? complete
          ? "complete"
          : "stopped"
        : stage.key === current.key && status === "NEEDS_SUPPLEMENT"
          ? "supplement"
          : complete
            ? "complete"
            : stage.key === current.key
              ? "current"
              : "pending",
      completedAt:
        settledAt ??
        (legacyFeeComplete
          ? (history.find((item) => item.toStatus === "PAID")?.createdAt ??
            null)
          : null) ??
        issued?.createdAt ??
        finalEvent?.createdAt ??
        exit?.createdAt ??
        null,
      detail:
        stage.key === "fee" && submissionFeeWaivedAt
          ? input.isTest || input.submissionFeeTestExempted
            ? "Được miễn phí kiểm thử"
            : "Được miễn phí"
          : stage.key === "fee" && submissionFeePaidAt
            ? "Đã thanh toán"
            : legacyFeeComplete
              ? "Đã thanh toán"
              : stage.key === current.key &&
                  (stopped || status === "NEEDS_SUPPLEMENT")
                ? (last?.note ?? null)
                : null,
    };
  });
  const next =
    stopped || status === "PUBLISHED"
      ? null
      : (definitions[definitions.indexOf(current) + 1]?.label ?? null);
  return {
    stages,
    current:
      status === "NEEDS_SUPPLEMENT"
        ? "Cần bạn bổ sung"
        : stopped
          ? "Hồ sơ đã dừng xử lý"
          : current.label,
    next,
    modern,
  };
}
