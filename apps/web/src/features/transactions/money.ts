const MONEY_PATTERN = /^(-?)(\d+)(?:\.(\d{1,2}))?$/;

/** Parse a plain CAD decimal without ever using floating-point arithmetic. */
export function parseCadToCents(value: string): number | null {
  const match = MONEY_PATTERN.exec(value.trim());
  if (!match) return null;
  const [, sign, whole, fraction = ''] = match;
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  const signed = sign === '-' ? -cents : cents;
  if (signed === 0n || signed > BigInt(Number.MAX_SAFE_INTEGER) || signed < BigInt(Number.MIN_SAFE_INTEGER)) return null;
  return Number(signed);
}

export function centsToInput(value: number): string {
  const sign = value < 0 ? '-' : '';
  const absolute = Math.abs(value);
  return `${sign}${Math.floor(absolute / 100)}.${String(absolute % 100).padStart(2, '0')}`;
}

export function formatCad(value: number): string {
  const sign = value < 0 ? '-' : '';
  const absolute = Math.abs(value);
  return `${sign}$${Math.floor(absolute / 100).toLocaleString('en-CA')}.${String(absolute % 100).padStart(2, '0')}`;
}
