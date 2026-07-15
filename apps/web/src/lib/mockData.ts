// Deterministic synthetic dataset shared by ALL three UI directions.
// NOT real statement data. Safe to commit. "Today" is treated as 2026-07-15.
import type {
  Account,
  Budget,
  Category,
  IncomeSchedule,
  RecurringSeries,
  Transaction,
} from './types';

export const TODAY = '2026-07-15';
export const CURRENT_MONTH = '2026-07-01';

export const categories: Category[] = [
  { id: 'housing', name: 'Housing', color: '#6366f1', icon: '🏠' },
  { id: 'groceries', name: 'Groceries', color: '#22c55e', icon: '🛒' },
  { id: 'dining', name: 'Dining & Takeaway', color: '#f97316', icon: '🍽️' },
  { id: 'transport', name: 'Transport', color: '#0ea5e9', icon: '🚗' },
  { id: 'health', name: 'Health', color: '#ec4899', icon: '💊' },
  { id: 'personal', name: 'Personal Care', color: '#a855f7', icon: '✂️' },
  { id: 'shopping', name: 'Shopping', color: '#eab308', icon: '🛍️' },
  { id: 'entertainment', name: 'Entertainment', color: '#14b8a6', icon: '🎬' },
  { id: 'savings', name: 'Savings', color: '#64748b', icon: '💰', excludedFromSpending: true },
  { id: 'debt', name: 'Debt Repayment', color: '#78716c', icon: '💳', excludedFromSpending: true },
  { id: 'fees', name: 'Fees & Interest', color: '#94a3b8', icon: '🏦', excludedFromSpending: true },
  { id: 'misc', name: 'Miscellaneous', color: '#8b5cf6', icon: '📦' },
  { id: 'uncategorized', name: 'Uncategorized', color: '#cbd5e1', icon: '❓' },
];

export const categoryById: Record<string, Category> = Object.fromEntries(
  categories.map((c) => [c.id, c]),
);

export const accounts: Account[] = [
  { id: 'td-visa', issuer: 'TD', name: 'TD Cash Back Visa', color: '#12805c', last4: '4821', currency: 'CAD' },
  { id: 'amex-cobalt', issuer: 'AMEX', name: 'Amex Cobalt', color: '#2f6fed', last4: '71007', currency: 'CAD' },
];

export const accountById: Record<string, Account> = Object.fromEntries(
  accounts.map((a) => [a.id, a]),
);

// --- Deterministic generator ---------------------------------------------

let seed = 1337;
function rand(): number {
  // Mulberry32-ish deterministic PRNG
  seed |= 0;
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function pick<T>(arr: T[]): T {
  return arr[Math.floor(rand() * arr.length)];
}
function between(min: number, max: number): number {
  return Math.round(min + rand() * (max - min));
}

interface MerchantSpec {
  merchant: string;
  raw: string;
  categoryId: string;
  min: number; // dollars
  max: number;
  account?: string;
}

const merchants: MerchantSpec[] = [
  { merchant: 'Loblaws', raw: 'LOBLAWS #1042 TORONTO ON', categoryId: 'groceries', min: 28, max: 165 },
  { merchant: 'Metro', raw: 'METRO 4471 QC', categoryId: 'groceries', min: 22, max: 140 },
  { merchant: 'Costco Wholesale', raw: 'COSTCO WHOLESALE W1287', categoryId: 'groceries', min: 90, max: 320 },
  { merchant: 'Tim Hortons', raw: 'TIM HORTONS #4821', categoryId: 'dining', min: 3, max: 22 },
  { merchant: 'Uber Eats', raw: 'UBER * EATS 8005928996', categoryId: 'dining', min: 18, max: 68 },
  { merchant: 'The Keg', raw: 'THE KEG STEAKHOUSE', categoryId: 'dining', min: 45, max: 180 },
  { merchant: 'Starbucks', raw: 'STARBUCKS #09912', categoryId: 'dining', min: 4, max: 19 },
  { merchant: 'Petro-Canada', raw: 'PETRO-CANADA 07731', categoryId: 'transport', min: 40, max: 95 },
  { merchant: 'Presto Transit', raw: 'PRESTO FARE/TRANSIT', categoryId: 'transport', min: 3, max: 12 },
  { merchant: 'Uber', raw: 'UBER * TRIP HELP.UBER.COM', categoryId: 'transport', min: 12, max: 55 },
  { merchant: 'Shoppers Drug Mart', raw: 'SHOPPERS DRUG MART #0821', categoryId: 'health', min: 12, max: 90 },
  { merchant: 'GoodLife Fitness', raw: 'GOODLIFE FITNESS CLUBS', categoryId: 'health', min: 45, max: 45 },
  { merchant: 'Amazon.ca', raw: 'AMZN Mktp CA*RT4X92', categoryId: 'shopping', min: 15, max: 220 },
  { merchant: 'Indigo', raw: 'INDIGO #0912 TORONTO', categoryId: 'shopping', min: 18, max: 95 },
  { merchant: 'Netflix', raw: 'NETFLIX.COM 866-579-7172', categoryId: 'entertainment', min: 21, max: 21 },
  { merchant: 'Spotify', raw: 'SPOTIFY P0C9F2A1B', categoryId: 'entertainment', min: 11, max: 11 },
  { merchant: 'Cineplex', raw: 'CINEPLEX #7130', categoryId: 'entertainment', min: 24, max: 78 },
  { merchant: 'Sephora', raw: 'SEPHORA 2144 QC', categoryId: 'personal', min: 25, max: 140 },
  { merchant: 'Great Clips', raw: 'GREAT CLIPS #4410', categoryId: 'personal', min: 28, max: 42 },
];

// Recurring subscriptions with fixed cadence (monthly).
const recurringMerchants = ['Netflix', 'Spotify', 'GoodLife Fitness'];

function iso(year: number, month: number, day: number): string {
  const m = String(month).padStart(2, '0');
  const d = String(day).padStart(2, '0');
  return `${year}-${m}-${d}`;
}

const daysInMonth: Record<number, number> = { 3: 31, 4: 30, 5: 31, 6: 30, 7: 15 };

function makeTransactions(): Transaction[] {
  const txns: Transaction[] = [];
  let n = 0;
  // Months: April(4) .. July(7 partial through the 15th).
  for (let month = 4; month <= 7; month++) {
    const maxDay = daysInMonth[month];
    // Recurring subscription charges (monthly, day 3–8).
    recurringMerchants.forEach((rm, i) => {
      const spec = merchants.find((m) => m.merchant === rm)!;
      const day = 3 + i * 2;
      if (day > maxDay) return;
      const cents = spec.min * 100;
      txns.push({
        id: `txn-${++n}`,
        accountId: spec.merchant === 'Netflix' ? 'amex-cobalt' : 'td-visa',
        date: iso(2026, month, day),
        postedDate: iso(2026, month, Math.min(day + 1, maxDay)),
        rawDescription: spec.raw,
        merchant: spec.merchant,
        amountCents: -cents,
        currency: 'CAD',
        type: 'purchase',
        categoryId: spec.categoryId,
        categorizationStatus: 'rule-applied',
        includedInSpending: true,
        recurringSeriesId: `rec-${rm.toLowerCase().replace(/\s+/g, '-')}`,
      });
    });

    // Rent (monthly, day 1) as an excluded transfer/housing.
    txns.push({
      id: `txn-${++n}`,
      accountId: 'td-visa',
      date: iso(2026, month, 1),
      postedDate: iso(2026, month, 1),
      rawDescription: 'PROPERTY MGMT PREAUTH RENT',
      merchant: 'Skyline Rentals',
      amountCents: -195000,
      currency: 'CAD',
      type: 'purchase',
      categoryId: 'housing',
      categorizationStatus: 'confirmed',
      includedInSpending: true,
      recurringSeriesId: 'rec-rent',
    });

    // Credit-card payment (excluded from spending).
    txns.push({
      id: `txn-${++n}`,
      accountId: 'td-visa',
      date: iso(2026, month, 12),
      postedDate: iso(2026, month, 12),
      rawDescription: 'PAYMENT - THANK YOU',
      merchant: 'Payment Received',
      amountCents: between(90000, 160000),
      currency: 'CAD',
      type: 'payment',
      categoryId: 'debt',
      categorizationStatus: 'rule-applied',
      includedInSpending: false,
      exclusionReason: 'Credit-card payment — excluded to avoid double-counting purchases.',
    });

    // Random discretionary purchases for the month.
    const count = between(22, 30);
    for (let i = 0; i < count; i++) {
      const spec = pick(merchants.filter((m) => !recurringMerchants.includes(m.merchant)));
      const day = between(1, maxDay);
      const cents = between(spec.min * 100, spec.max * 100);
      const account = spec.account ?? (rand() > 0.5 ? 'td-visa' : 'amex-cobalt');
      // A few remain unreviewed in the current (partial) month.
      const isCurrent = month === 7;
      const uncertain = isCurrent && rand() > 0.72;
      txns.push({
        id: `txn-${++n}`,
        accountId: account,
        date: iso(2026, month, day),
        postedDate: iso(2026, month, Math.min(day + 1, maxDay)),
        rawDescription: spec.raw,
        merchant: spec.merchant,
        amountCents: -cents,
        currency: 'CAD',
        type: 'purchase',
        categoryId: uncertain ? null : spec.categoryId,
        categorizationStatus: uncertain ? 'suggested' : (rand() > 0.5 ? 'confirmed' : 'rule-applied'),
        confidence: uncertain ? Number((0.55 + rand() * 0.4).toFixed(2)) : undefined,
        reason: uncertain ? `Matched merchant keyword "${spec.merchant.split(' ')[0]}"` : undefined,
        includedInSpending: true,
      });
    }

    // One refund per month.
    if (rand() > 0.35) {
      const spec = pick(merchants.filter((m) => m.categoryId === 'shopping'));
      const day = between(5, maxDay);
      txns.push({
        id: `txn-${++n}`,
        accountId: 'amex-cobalt',
        date: iso(2026, month, day),
        postedDate: iso(2026, month, Math.min(day + 2, maxDay)),
        rawDescription: `${spec.raw} REFUND`,
        merchant: spec.merchant,
        amountCents: between(1500, 8000),
        currency: 'CAD',
        type: 'refund',
        categoryId: spec.categoryId,
        categorizationStatus: 'confirmed',
        includedInSpending: true,
        reason: 'Refund reduces net spending in the original category.',
      });
    }

    // Interest / fee occasionally (excluded).
    if (month % 2 === 0) {
      txns.push({
        id: `txn-${++n}`,
        accountId: 'td-visa',
        date: iso(2026, month, 20 > maxDay ? maxDay : 20),
        rawDescription: 'INTEREST CHARGE ON PURCHASES',
        merchant: 'Interest',
        amountCents: -between(400, 2200),
        currency: 'CAD',
        type: 'interest',
        categoryId: 'fees',
        categorizationStatus: 'rule-applied',
        includedInSpending: false,
        exclusionReason: 'Interest — excluded from core spending by default.',
      });
    }
  }
  return txns.sort((a, b) => (a.date < b.date ? 1 : -1));
}

export const transactions: Transaction[] = makeTransactions();

export const recurringSeries: RecurringSeries[] = [
  { id: 'rec-netflix', accountId: 'amex-cobalt', name: 'Netflix', merchant: 'Netflix', categoryId: 'entertainment', expectedAmountCents: 2100, cadence: 'monthly', nextExpectedDate: '2026-08-03', confidence: 0.98, status: 'keep', reason: '4 charges, exact $21.00 monthly.' },
  { id: 'rec-spotify', accountId: 'td-visa', name: 'Spotify', merchant: 'Spotify', categoryId: 'entertainment', expectedAmountCents: 1100, cadence: 'monthly', nextExpectedDate: '2026-08-05', confidence: 0.97, status: 'keep', reason: '4 charges, exact $11.00 monthly.' },
  { id: 'rec-goodlife-fitness', accountId: 'td-visa', name: 'GoodLife Fitness', merchant: 'GoodLife Fitness', categoryId: 'health', expectedAmountCents: 4500, cadence: 'monthly', nextExpectedDate: '2026-08-07', confidence: 0.95, status: 'review', reason: '4 charges, exact $45.00 monthly. Consider reviewing usage.' },
  { id: 'rec-rent', accountId: 'td-visa', name: 'Rent — Skyline Rentals', merchant: 'Skyline Rentals', categoryId: 'housing', expectedAmountCents: 195000, cadence: 'monthly', nextExpectedDate: '2026-08-01', confidence: 0.99, status: 'keep', reason: 'Fixed $1,950.00 on the 1st.' },
];

export const incomeSchedules: IncomeSchedule[] = [
  { id: 'inc-salary', name: 'Acme Corp — Payroll', amountCents: 262500, frequency: 'biweekly', nextDate: '2026-07-24', active: true },
  { id: 'inc-freelance', name: 'Freelance (design)', amountCents: 80000, frequency: 'monthly', nextDate: '2026-07-28', active: true },
];

export const budgets: Budget[] = [
  { categoryId: null, monthlyLimitCents: 320000 }, // overall
  { categoryId: 'groceries', monthlyLimitCents: 70000 },
  { categoryId: 'dining', monthlyLimitCents: 45000 },
  { categoryId: 'transport', monthlyLimitCents: 30000 },
  { categoryId: 'shopping', monthlyLimitCents: 40000 },
  { categoryId: 'entertainment', monthlyLimitCents: 15000 },
];

export const profile = { id: 'me', name: 'Hayden', initials: 'H' };
