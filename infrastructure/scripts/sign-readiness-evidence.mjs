import { createPrivateKey, sign } from "node:crypto";
import { readFile, stat, writeFile } from "node:fs/promises";

import { readAndValidateEvidence } from "./readiness-evidence.mjs";

const [evidencePath, signaturePath] = process.argv.slice(2);
const keyPath = process.env.READINESS_EVIDENCE_PRIVATE_KEY_FILE;
if (!evidencePath || !signaturePath || !keyPath) {
  console.error(
    "usage: READINESS_EVIDENCE_PRIVATE_KEY_FILE=<path> sign-readiness-evidence.mjs <evidence.json> <evidence.sig>",
  );
  process.exit(64);
}

try {
  if ((await stat(keyPath)).size > 16_384) {
    throw new Error("readiness signing key exceeds the size limit");
  }
  const [{ raw }, key] = await Promise.all([
    readAndValidateEvidence(evidencePath),
    readFile(keyPath),
  ]);
  const signature = sign(null, raw, createPrivateKey(key)).toString("base64");
  await writeFile(signaturePath, `${signature}\n`, { mode: 0o600 });
  process.stderr.write("readiness evidence signed\n");
} catch (error) {
  console.error(
    error instanceof Error ? error.message : "evidence signing failed",
  );
  process.exit(1);
}
