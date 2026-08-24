import assert from "node:assert/strict";
import test from "node:test";

import { parseMainnetBroadcastEvidence } from "./read-thv-proof-registry-mainnet-broadcast-evidence.mjs";

const EXPECTED_DEPLOYER = "0x1234567890123456789012345678901234567890";
const CONTRACT_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd";
const TRANSACTION_HASH = `0x${"ab".repeat(32)}`;

function evidence({ chain = 137, from = EXPECTED_DEPLOYER } = {}) {
  return {
    chain,
    transactions: [
      {
        hash: TRANSACTION_HASH,
        transactionType: "CREATE",
        contractName: "THVProofRegistry",
        contractAddress: CONTRACT_ADDRESS,
        transaction: {
          from,
          chainId: "0x89",
        },
      },
    ],
  };
}

test("accepts valid Polygon Mainnet THVProofRegistry broadcast evidence", () => {
  const result = parseMainnetBroadcastEvidence(evidence(), EXPECTED_DEPLOYER);

  assert.deepEqual(result, {
    contractAddress: CONTRACT_ADDRESS.toLowerCase(),
    transactionHash: TRANSACTION_HASH.toLowerCase(),
  });
});

test("rejects prior evidence from a chain other than Polygon Mainnet", () => {
  assert.throws(
    () => parseMainnetBroadcastEvidence(evidence({ chain: 80002 }), EXPECTED_DEPLOYER),
    /chain is not 137/,
  );
});

test("rejects prior evidence broadcast by an unexpected deployer", () => {
  assert.throws(
    () =>
      parseMainnetBroadcastEvidence(
        evidence({ from: "0x9999999999999999999999999999999999999999" }),
        EXPECTED_DEPLOYER,
      ),
    /sender does not match EXPECTED_DEPLOYER/,
  );
});
