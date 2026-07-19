// Category wire types — mirror apps/api/app/schemas/category.py exactly.

export interface Category {
  id: number;
  profile_id: number;
  slug: string;
  name: string;
  color: string;
  icon: string;
  parent_id: number | null;
  excluded_from_spending: boolean;
  is_default: boolean;
  sort_order: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryCreate {
  name: string;
  color: string;
  icon?: string;
  parent_id?: number | null;
  excluded_from_spending?: boolean;
}

export interface CategoryUpdate {
  name?: string;
  color?: string;
  icon?: string;
  excluded_from_spending?: boolean;
  sort_order?: number;
  is_archived?: boolean;
}

export const CATEGORY_COLORS = [
  '#6366f1',
  '#22c55e',
  '#f97316',
  '#0ea5e9',
  '#ec4899',
  '#a855f7',
  '#eab308',
  '#14b8a6',
  '#64748b',
  '#8b5cf6',
];

export type CategoryIconName =
  | 'home' | 'groceries' | 'dining' | 'transport' | 'health' | 'personal'
  | 'shopping' | 'entertainment' | 'income' | 'card' | 'bank' | 'package'
  | 'gift' | 'travel' | 'phone' | 'pet' | 'heart' | 'nightlife' | 'category';

export const CATEGORY_ICON_CHOICES: ReadonlyArray<{ value: CategoryIconName; label: string }> = [
  { value: 'home', label: 'Home' },
  { value: 'groceries', label: 'Groceries' },
  { value: 'dining', label: 'Dining' },
  { value: 'transport', label: 'Transport' },
  { value: 'health', label: 'Health' },
  { value: 'personal', label: 'Personal care' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'income', label: 'Income' },
  { value: 'card', label: 'Card' },
  { value: 'bank', label: 'Bank' },
  { value: 'package', label: 'Package' },
  { value: 'gift', label: 'Gift' },
  { value: 'travel', label: 'Travel' },
  { value: 'phone', label: 'Phone' },
  { value: 'pet', label: 'Pet' },
  { value: 'heart', label: 'Relationship' },
  { value: 'nightlife', label: 'Going out' },
];
