const LEGACY_DOSSIER_PREFIX = "TMI-";

/**
 * Shows legacy dossier identifiers under the CNS identity without mutating the
 * signed source record. Certificate numbers themselves are never rewritten
 * here: revoked certificates must remain traceable by their original number.
 */
export function displayCnsDossierCode(code: string | null | undefined): string {
  if (!code) return "";
  return code.startsWith(LEGACY_DOSSIER_PREFIX)
    ? `CNS-${code.slice(LEGACY_DOSSIER_PREFIX.length)}`
    : code;
}
