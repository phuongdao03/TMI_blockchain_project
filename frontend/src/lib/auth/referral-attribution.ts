import { affiliateApi } from "@/lib/api/client";

const STORAGE_KEY = "thv.affiliate.referral-attribution";
let pendingRecord: Promise<ReferralAttribution | null> | null = null;

export interface ReferralAttribution {
  referralCode: string;
  eventId: string;
  clickId?: string;
}

function isReferralAttribution(value: unknown): value is ReferralAttribution {
  if (!value || typeof value !== "object") return false;
  const attribution = value as Partial<ReferralAttribution>;
  return (
    typeof attribution.referralCode === "string" &&
    /^[A-Za-z0-9-]{8,32}$/.test(attribution.referralCode) &&
    typeof attribution.eventId === "string" &&
    /^[0-9a-f-]{36}$/i.test(attribution.eventId) &&
    (attribution.clickId === undefined ||
      (typeof attribution.clickId === "string" &&
        /^[0-9a-f-]{36}$/i.test(attribution.clickId)))
  );
}

function newEventId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (part) => {
    const random = Math.floor(Math.random() * 16);
    return (part === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

export function getReferralAttribution(): ReferralAttribution | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (isReferralAttribution(value)) return value;
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    return null;
  }
  return null;
}

export function captureReferralCode(
  code?: string | null,
): ReferralAttribution | null {
  const existing = getReferralAttribution();
  if (existing) return existing;
  const referralCode = code?.trim();
  if (!referralCode || !/^[A-Za-z0-9-]{8,32}$/.test(referralCode)) return null;
  const attribution = { referralCode, eventId: newEventId() };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution));
    return attribution;
  } catch {
    return null;
  }
}

export function clearReferralAttribution() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}

export async function ensureReferralAttribution(
  code?: string | null,
): Promise<ReferralAttribution | null> {
  const attribution = captureReferralCode(code);
  if (!attribution || attribution.clickId) return attribution;
  if (pendingRecord) return pendingRecord;
  pendingRecord = (async () => {
    try {
      const click = await affiliateApi.recordReferralClick(
        attribution.referralCode,
        attribution.eventId,
      );
      const recorded = { ...attribution, clickId: click.id };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(recorded));
      return recorded;
    } catch {
      return attribution;
    } finally {
      pendingRecord = null;
    }
  })();
  return pendingRecord;
}
