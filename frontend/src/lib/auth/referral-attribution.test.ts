import { beforeEach, describe, expect, it, vi } from "vitest";

const affiliateApi = vi.hoisted(() => ({ recordReferralClick: vi.fn() }));

vi.mock("@/lib/api/client", () => ({ affiliateApi }));

import {
  captureReferralCode,
  ensureReferralAttribution,
  getReferralAttribution,
} from "./referral-attribution";

describe("referral attribution storage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    affiliateApi.recordReferralClick.mockResolvedValue({
      id: "0d7f1d18-e455-4a7a-9df0-fce15fc9223a",
      createdAt: "2026-11-05T00:00:00Z",
    });
  });

  it("persists a code and records one idempotent click before exchange", async () => {
    const captured = captureReferralCode("THV-ABC123");
    expect(captured?.eventId).toMatch(/^[0-9a-f-]{36}$/i);

    const [first, concurrent] = await Promise.all([
      ensureReferralAttribution(),
      ensureReferralAttribution("THV-ABC123"),
    ]);

    expect(affiliateApi.recordReferralClick).toHaveBeenCalledTimes(1);
    expect(affiliateApi.recordReferralClick).toHaveBeenCalledWith(
      "THV-ABC123",
      captured?.eventId,
    );
    expect(first?.clickId).toBe("0d7f1d18-e455-4a7a-9df0-fce15fc9223a");
    expect(concurrent).toEqual(first);
    expect(getReferralAttribution()).toEqual(first);
    await ensureReferralAttribution();
    expect(affiliateApi.recordReferralClick).toHaveBeenCalledTimes(1);
  });

  it("keeps the first referral code for attribution", () => {
    captureReferralCode("THV-ABC123");
    const second = captureReferralCode("THV-XYZ987");

    expect(second?.referralCode).toBe("THV-ABC123");
  });
});
