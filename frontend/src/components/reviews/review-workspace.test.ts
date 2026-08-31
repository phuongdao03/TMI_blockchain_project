import { describe, expect, it } from "vitest";

import { reviewDeadlineState } from "@/components/reviews/review-workspace";

describe("reviewDeadlineState", () => {
  it("distinguishes overdue assignments from assignments still within SLA", () => {
    const now = new Date("2026-08-29T08:00:00Z");

    expect(reviewDeadlineState("2026-08-29T06:00:00Z", now).status).toBe(
      "OVERDUE",
    );
    expect(reviewDeadlineState("2026-08-30T08:00:00Z", now).status).toBe(
      "ON_TRACK",
    );
    expect(reviewDeadlineState(null, now).status).toBe("UNSCHEDULED");
  });
});
