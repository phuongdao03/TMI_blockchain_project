"use client";

interface RiskItem {
  label: string;
  value: number;
  color: string;
}

export function OperationsRiskChart({
  blockchainFailures,
  overdueReviews,
  paymentFailures,
}: {
  blockchainFailures: number;
  overdueReviews: number;
  paymentFailures: number;
}) {
  const items: RiskItem[] = [
    {
      label: "Hồ sơ trễ hạn",
      value: overdueReviews,
      color: "var(--theme-accent)",
    },
    {
      label: "Thanh toán lỗi",
      value: paymentFailures,
      color: "var(--theme-gold)",
    },
    {
      label: "Phát hành lỗi",
      value: blockchainFailures,
      color: "var(--theme-warning)",
    },
  ];
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div
      aria-label="Biểu đồ cơ cấu cảnh báo vận hành"
      className="grid gap-5 sm:grid-cols-[10rem_1fr] sm:items-center"
      role="img"
    >
      <div className="relative mx-auto size-40">
        <svg aria-hidden="true" className="size-full" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            fill="none"
            r={radius}
            stroke="var(--theme-elevated)"
            strokeWidth="14"
          />
          {total > 0
            ? items.map((item) => {
                const length = (item.value / total) * circumference;
                const segment = (
                  <circle
                    cx="60"
                    cy="60"
                    fill="none"
                    key={item.label}
                    r={radius}
                    stroke={item.color}
                    strokeDasharray={`${length} ${circumference - length}`}
                    strokeDashoffset={-offset}
                    strokeWidth="14"
                    transform="rotate(-90 60 60)"
                  />
                );
                offset += length;
                return segment;
              })
            : null}
        </svg>
        <div className="absolute inset-0 grid place-content-center text-center">
          <strong className="text-3xl tabular-nums">{total}</strong>
          <span className="text-[0.65rem] font-bold uppercase tracking-wider text-neutral-500">
            cảnh báo
          </span>
        </div>
      </div>
      <ul className="space-y-3" role="list">
        {items.map((item) => (
          <li className="flex items-center gap-3" key={item.label}>
            <span
              aria-hidden="true"
              className="size-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="min-w-0 flex-1 text-sm text-neutral-600">
              {item.label}
            </span>
            <strong className="font-mono text-sm tabular-nums">
              {item.value}
            </strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ReviewerWorkloadChart({
  rows,
}: {
  rows: Array<{ reviewerEmail: string; activeAssignments: number }>;
}) {
  const max = Math.max(1, ...rows.map((row) => row.activeAssignments));
  return (
    <div
      aria-label="Biểu đồ khối lượng theo chuyên viên"
      className="space-y-4"
      role="img"
    >
      {rows.length ? (
        rows.map((row) => (
          <div
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 sm:grid-cols-[minmax(9rem,1fr)_2fr_auto]"
            key={row.reviewerEmail}
          >
            <span
              className="truncate text-sm font-semibold"
              title={row.reviewerEmail}
            >
              {row.reviewerEmail}
            </span>
            <div className="order-3 col-span-2 h-3 overflow-hidden rounded-full bg-[var(--theme-elevated)] sm:order-none sm:col-span-1">
              <div
                aria-hidden="true"
                className="h-full rounded-full bg-primary-600"
                style={{
                  width: `${Math.max(5, (row.activeAssignments / max) * 100)}%`,
                }}
              />
            </div>
            <strong className="font-mono text-sm tabular-nums">
              {row.activeAssignments}
            </strong>
          </div>
        ))
      ) : (
        <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-6 text-center text-sm text-neutral-500">
          Chưa có phân công đang hoạt động.
        </p>
      )}
    </div>
  );
}
