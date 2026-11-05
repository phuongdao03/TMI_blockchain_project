"use client";

import { useEffect } from "react";

import { ensureReferralAttribution } from "@/lib/auth/referral-attribution";

export function ReferralAttributionCapture() {
  useEffect(() => {
    const referralCode = new URLSearchParams(window.location.search).get("ref");
    if (referralCode) void ensureReferralAttribution(referralCode);
  }, []);

  return null;
}
