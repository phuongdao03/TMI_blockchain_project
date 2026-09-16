const CERTIFICATE_NUMBER = /^CNS-\d{4}-[A-Z0-9-]{4,64}$/i;

export function isCertificateNumber(value: string): boolean {
  return CERTIFICATE_NUMBER.test(value.trim());
}
