import { beforeEach, expect, it } from "vitest";

import {
  clearPendingProofBroadcast,
  readPendingProofBroadcast,
  savePendingProofBroadcast,
} from "@/lib/blockchain/pending-proof-broadcast";

const pending = {
  dossierId: "dossier-1",
  version: 1,
  transactionId: "transaction-1",
  intentId: "intent-1",
  transactionHash: `0x${"ab".repeat(32)}`,
  connectedWallet: `0x${"cd".repeat(20)}`,
};

beforeEach(() => window.localStorage.clear());

it("keeps an unacknowledged wallet hash across reloads and clears only that hash", () => {
  savePendingProofBroadcast(pending);
  expect(readPendingProofBroadcast("dossier-1", 1)).toEqual(pending);
  clearPendingProofBroadcast({
    ...pending,
    transactionHash: `0x${"11".repeat(32)}`,
  });
  expect(readPendingProofBroadcast("dossier-1", 1)).toEqual(pending);
  clearPendingProofBroadcast(pending);
  expect(readPendingProofBroadcast("dossier-1", 1)).toBeNull();
});

it("ignores malformed pending hashes", () => {
  window.localStorage.setItem(
    "thv-proof-broadcast:dossier-1:1",
    JSON.stringify({ ...pending, transactionHash: "not-a-hash" }),
  );
  expect(readPendingProofBroadcast("dossier-1", 1)).toBeNull();
});
