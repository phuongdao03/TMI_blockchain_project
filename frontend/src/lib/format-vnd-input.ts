export function parseVndInput(value: string): string {
  return value.replace(/\D/g, "").replace(/^0+(?=\d)/, "");
}

export function formatVndInput(value: string): string {
  const digits = parseVndInput(value);
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}
