"""Canonical default spending categories seeded per profile.

Kept in sync with the frontend synthetic dataset
(`apps/web/src/lib/mockData.ts`). Order is the seeded ``sort_order``.
"""

from __future__ import annotations

from typing import NamedTuple


class DefaultCategory(NamedTuple):
    slug: str
    name: str
    color: str
    icon: str
    excluded_from_spending: bool


DEFAULT_CATEGORIES: tuple[DefaultCategory, ...] = (
    DefaultCategory("housing", "Housing", "#6366f1", "🏠", False),
    DefaultCategory("groceries", "Groceries", "#22c55e", "🛒", False),
    DefaultCategory("dining", "Dining & Takeaway", "#f97316", "🍽️", False),
    DefaultCategory("transport", "Transport", "#0ea5e9", "🚗", False),
    DefaultCategory("health", "Health", "#ec4899", "💊", False),
    DefaultCategory("personal", "Personal Care", "#a855f7", "✂️", False),
    DefaultCategory("shopping", "Shopping", "#eab308", "🛍️", False),
    DefaultCategory("entertainment", "Entertainment", "#14b8a6", "🎬", False),
    DefaultCategory("going-out", "Going Out", "#f43f5e", "nightlife", False),
    DefaultCategory("relationship", "Relationship", "#e11d48", "heart", False),
    DefaultCategory("savings", "Savings", "#64748b", "💰", True),
    DefaultCategory("debt", "Debt Repayment", "#78716c", "💳", True),
    DefaultCategory("fees", "Fees & Interest", "#94a3b8", "🏦", True),
    DefaultCategory("misc", "Miscellaneous", "#8b5cf6", "📦", False),
    DefaultCategory("uncategorized", "Uncategorized", "#cbd5e1", "❓", False),
)
