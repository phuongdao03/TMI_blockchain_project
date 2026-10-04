const LEGACY_DOSSIER_PREFIXES = ["TMI-", "CNS-"];

/**
 * Avoids displaying old brand codes in the current interface while preserving
 * the original identifier in the signed source record.
 */
export function displayCnsDossierCode(code: string | null | undefined): string {
  if (!code) return "";
  return LEGACY_DOSSIER_PREFIXES.some((prefix) => code.startsWith(prefix))
    ? "Hồ sơ lưu trữ"
    : code;
}
