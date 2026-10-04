const LEGACY_DOSSIER_PREFIXES = ["TMI-", "CNS-"];

/**
 * Avoids displaying old brand codes in the current interface while preserving
 * the original identifier in the signed source record.
 */
export function displayCnsDossierCode(code: string | null | undefined): string {
  if (!code) return "";
  const legacyPrefix = LEGACY_DOSSIER_PREFIXES.find((prefix) =>
    code.startsWith(prefix),
  );
  return legacyPrefix ? `THV-${code.slice(legacyPrefix.length)}` : code;
}
