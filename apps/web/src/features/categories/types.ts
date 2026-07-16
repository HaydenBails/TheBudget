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

export const ICON_CHOICES = ['🏠', '🛒', '🍽️', '🚗', '💊', '✂️', '🛍️', '🎬', '💰', '💳', '🏦', '📦', '🎁', '✈️', '📱', '🐾'];
