// Formatting helpers. Money is stored as integer cents; format at the edge only.

const CAD = new Intl.NumberFormat('en-CA', {
  style: 'currency',
  currency: 'CAD',
});

const CAD_NO_CENTS = new Intl.NumberFormat('en-CA', {
  style: 'currency',
  currency: 'CAD',
  maximumFractionDigits: 0,
});

/** Format signed integer cents as CAD, e.g. -12345 -> "-$123.45". */
export function formatCents(cents: number): string {
  return CAD.format(cents / 100);
}

/** Absolute value formatting (magnitude), useful for spending displays. */
export function formatCentsAbs(cents: number): string {
  return CAD.format(Math.abs(cents) / 100);
}

/** Compact whole-dollar formatting for big headline numbers. */
export function formatDollarsAbs(cents: number): string {
  return CAD_NO_CENTS.format(Math.abs(cents) / 100);
}

/** e.g. "Jul 14" */
export function formatShortDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}

/** e.g. "July 2026" */
export function formatMonthLabel(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
}

/** Signed percentage, e.g. 0.123 -> "+12.3%". */
export function formatSignedPct(fraction: number): string {
  const sign = fraction > 0 ? '+' : '';
  return `${sign}${(fraction * 100).toFixed(1)}%`;
}
