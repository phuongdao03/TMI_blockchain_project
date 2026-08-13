import { createPublicKey, verify } from "node:crypto";
import { readFile, stat } from "node:fs/promises";

import { readAndValidateEvidence } from "./readiness-evidence.mjs";

const [evidencePath, signaturePath] = process.argv.slice(2);
const keyPath = process.env.READINESS_EVIDENCE_PUBLIC_KEY_FILE;
if (!evidencePath || !signaturePath || !keyPath) {
  console.error(
    "usage: READINESS_EVIDENCE_PUBLIC_KEY_FILE=<path> verify-readiness-evidence.mjs <evidence.json> <evidence.sig>",
  );
  process.exit(64);
}

try {
  const [signatureStat, keyStat] = await Promise.all([
    stat(signaturePath),
    stat(keyPath),
  ]);
  if (signatureStat.size > 1_024 || keyStat.size > 16_384) {
    throw new Error("readiness verification input exceeds the size limit");
  }
  const [{ raw, value }, signature, key] = await Promise.all([
    readAndValidateEvidence(evidencePath),
    readFile(signaturePath, "utf8"),
    readFile(keyPath),
  ]);
  const verified = verify(
    null,
    raw,
    createPublicKey(key),
    Buffer.from(signature.trim(), "base64"),
  );
  if (!verified) throw new Error("readiness evidence signature is invalid");
  process.stdout.write(
    `${JSON.stringify({ verified: true, status: value.status, drillType: value.drillType })}\n`,
  );
} catch (error) {
  console.error(
    error instanceof Error ? error.message : "evidence verification failed",
  );
  process.exit(1);
}
