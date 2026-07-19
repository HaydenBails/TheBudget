import type { ReactNode } from 'react';
import type { CategoryIconName } from './types';

const PATHS: Record<CategoryIconName, ReactNode> = {
  home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v11h14V10M9 21v-7h6v7" /></>,
  groceries: <><circle cx="9" cy="20" r="1" /><circle cx="19" cy="20" r="1" /><path d="M3 4h2l2.4 10.2a2 2 0 0 0 2 1.5h7.8a2 2 0 0 0 2-1.6L21 8H7" /></>,
  dining: <><path d="M7 3v8M4 3v5a3 3 0 0 0 6 0V3M7 11v10M17 3v18M17 3c3 2 3 7 0 9" /></>,
  transport: <><path d="m5 17-1 2M19 17l1 2M3 13l2-6h14l2 6v5H3Z" /><circle cx="7" cy="15" r="1" /><circle cx="17" cy="15" r="1" /></>,
  health: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />,
  personal: <><circle cx="6" cy="6" r="3" /><circle cx="18" cy="18" r="3" /><path d="m8.1 8.1 7.8 7.8M14.5 5.5 4 16M19.5 4.5 16 8" /></>,
  shopping: <><path d="M6 8h12l1 13H5L6 8Z" /><path d="M9 9V6a3 3 0 0 1 6 0v3" /></>,
  entertainment: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m10 9 5 3-5 3Z" /></>,
  income: <><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M16 10h5M7 12h4M9 10v4" /></>,
  card: <><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20M6 15h4" /></>,
  bank: <><path d="m3 9 9-5 9 5M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18" /></>,
  package: <><path d="m4 7 8-4 8 4-8 4-8-4Z" /><path d="M4 7v10l8 4 8-4V7M12 11v10" /></>,
  gift: <><rect x="3" y="8" width="18" height="13" rx="1" /><path d="M12 8v13M3 12h18M7.5 8C4 8 4 3 7 3c2 0 5 5 5 5M16.5 8C20 8 20 3 17 3c-2 0-5 5-5 5" /></>,
  travel: <path d="m22 2-7 20-4-9-9-4 20-7Z" />,
  phone: <><rect x="6" y="2" width="12" height="20" rx="2" /><path d="M10 18h4" /></>,
  pet: <><circle cx="6" cy="7" r="2" /><circle cx="18" cy="7" r="2" /><circle cx="9" cy="4" r="2" /><circle cx="15" cy="4" r="2" /><path d="M8 15c0-3 2-5 4-5s4 2 4 5c0 3-2 5-4 5s-4-2-4-5Z" /></>,
  heart: <path d="M12 21s-7.5-4.6-10-9A5 5 0 0 1 12 6a5 5 0 0 1 10 6c-2.5 4.4-10 9-10 9Z" />,
  nightlife: <><path d="M5 4h14l-7 8-7-8Z" /><path d="M12 12v6M8 21h8" /></>,
  category: <><path d="M20.6 13.6 11 4H4v7l9.6 9.6a2 2 0 0 0 2.8 0l4.2-4.2a2 2 0 0 0 0-2.8Z" /><circle cx="7.5" cy="7.5" r=".5" /></>,
};

const legacy = (...codePoints: number[]) => String.fromCodePoint(...codePoints);
const LEGACY_ALIASES: Record<string, CategoryIconName> = {
  [legacy(0x1f3e0)]: 'home', [legacy(0x1f6d2)]: 'groceries', [legacy(0x1f37d, 0xfe0f)]: 'dining',
  [legacy(0x1f697)]: 'transport', [legacy(0x1f48a)]: 'health', [legacy(0x2702, 0xfe0f)]: 'personal',
  [legacy(0x1f6cd, 0xfe0f)]: 'shopping', [legacy(0x1f3ac)]: 'entertainment', [legacy(0x1f4b0)]: 'income',
  [legacy(0x1f4b3)]: 'card', [legacy(0x1f3e6)]: 'bank', [legacy(0x1f4e6)]: 'package',
  [legacy(0x1f381)]: 'gift', [legacy(0x2708, 0xfe0f)]: 'travel', [legacy(0x1f4f1)]: 'phone',
  [legacy(0x1f43e)]: 'pet',
};

export function normalizeCategoryIcon(value?: string | null): CategoryIconName {
  if (value && value in PATHS) return value as CategoryIconName;
  return value ? LEGACY_ALIASES[value] ?? 'category' : 'category';
}

export function CategoryIcon({ name, label }: { name?: string | null; label?: string }) {
  const normalized = normalizeCategoryIcon(name);
  return (
    <svg className="ct-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" role={label ? 'img' : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      {PATHS[normalized]}
    </svg>
  );
}
