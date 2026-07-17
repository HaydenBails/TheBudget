"""Profile-isolated merchant → category rules and auto-categorization.

A rule maps a normalized merchant pattern to a category. Rules are matched
against a transaction's merchant/description to suggest or apply a category, so
importing and reviewing get faster the more the user (and the generic seed)
teaches. Services flush but do not commit; the API owns transaction boundaries.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, MerchantRule, Transaction
from app.schemas import MerchantRuleCreate, MerchantRuleUpdate
from app.services.errors import InvalidUpdateError, ResourceNotFoundError
from app.services.merchant_rules_data import DEFAULT_MERCHANT_RULES
from app.services.profiles import require_profile

_PRIORITY = {"exact": 3, "prefix": 2, "contains": 1}


def normalize_search_text(merchant: str, raw_description: str) -> str:
    """Uppercase alphanumeric text used for 'contains'/'prefix' matching."""

    combined = f"{merchant or ''} {raw_description or ''}".upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]+", " ", combined).split())


def normalize_merchant_key(merchant: str, raw_description: str) -> str:
    """Stable letters-only key (first four tokens) for exact-merchant rules."""

    base = (merchant or raw_description or "").upper()
    return " ".join(re.sub(r"[^A-Z ]+", " ", base).split()[:4])


@dataclass(frozen=True, slots=True)
class _Observation:
    key: str
    text: str


def _observe(merchant: str, raw_description: str) -> _Observation:
    return _Observation(
        key=normalize_merchant_key(merchant, raw_description),
        text=normalize_search_text(merchant, raw_description),
    )


def _rule_matches(rule: MerchantRule, observation: _Observation) -> bool:
    if rule.match_type == "exact":
        return bool(rule.pattern) and rule.pattern == observation.key
    if rule.match_type == "prefix":
        return bool(rule.pattern) and observation.key.startswith(rule.pattern)
    return bool(rule.pattern) and rule.pattern in observation.text


def _best_match(rules: list[MerchantRule], observation: _Observation) -> MerchantRule | None:
    best: MerchantRule | None = None
    best_rank: tuple[int, int, int] = (0, 0, -1)
    for rule in rules:
        if not rule.is_active or not _rule_matches(rule, observation):
            continue
        rank = (_PRIORITY[rule.match_type], len(rule.pattern), rule.hit_count)
        if best is None or rank > best_rank:
            best, best_rank = rule, rank
    return best


def _active_rules(session: Session, profile_id: int) -> list[MerchantRule]:
    return list(
        session.scalars(
            select(MerchantRule).where(
                MerchantRule.profile_id == profile_id,
                MerchantRule.is_active.is_(True),
            )
        )
    )


def suggest_category_id(
    session: Session, profile_id: int, merchant: str, raw_description: str
) -> int | None:
    """Return the category a rule would assign, without persisting anything."""

    match = _best_match(_active_rules(session, profile_id), _observe(merchant, raw_description))
    return match.category_id if match is not None else None


def apply_rules_to_uncategorized(session: Session, profile_id: int) -> int:
    """Auto-categorize every uncategorized transaction that a rule matches."""

    require_profile(session, profile_id)
    rules = _active_rules(session, profile_id)
    if not rules:
        return 0
    excluded = {
        category.id: category.excluded_from_spending
        for category in session.scalars(
            select(Category).where(Category.profile_id == profile_id)
        )
    }
    pending = session.scalars(
        select(Transaction).where(
            Transaction.profile_id == profile_id,
            Transaction.deleted_at.is_(None),
            Transaction.category_id.is_(None),
        )
    )
    categorized = 0
    for transaction in pending:
        match = _best_match(rules, _observe(transaction.merchant, transaction.raw_description))
        if match is None:
            continue
        transaction.category_id = match.category_id
        transaction.categorization_status = "rule_applied"
        if excluded.get(match.category_id, False):
            transaction.included_in_spending = False
        match.hit_count += 1
        categorized += 1
    session.flush()
    return categorized


def learn_rule(
    session: Session, profile_id: int, merchant: str, raw_description: str, category_id: int
) -> MerchantRule:
    """Remember an exact-merchant rule from a manual categorization."""

    key = normalize_merchant_key(merchant, raw_description)
    if not key:
        raise InvalidUpdateError("cannot learn a rule from a blank merchant")
    existing = session.scalar(
        select(MerchantRule).where(
            MerchantRule.profile_id == profile_id,
            MerchantRule.pattern == key,
            MerchantRule.match_type == "exact",
        )
    )
    if existing is not None:
        existing.category_id = category_id
        existing.is_active = True
        existing.hit_count += 1
        session.flush()
        return existing
    rule = MerchantRule(
        profile_id=profile_id,
        category_id=category_id,
        pattern=key,
        match_type="exact",
        hit_count=1,
    )
    session.add(rule)
    session.flush()
    return rule


def learn_from_history(session: Session, profile_id: int) -> tuple[int, int]:
    """Build exact rules from already-categorized transactions (majority wins)."""

    require_profile(session, profile_id)
    rows = session.scalars(
        select(Transaction).where(
            Transaction.profile_id == profile_id,
            Transaction.deleted_at.is_(None),
            Transaction.category_id.is_not(None),
        )
    )
    votes: dict[str, Counter[int]] = defaultdict(Counter)
    for row in rows:
        key = normalize_merchant_key(row.merchant, row.raw_description)
        if key and row.category_id is not None:
            votes[key][row.category_id] += 1

    existing = {
        rule.pattern: rule
        for rule in session.scalars(
            select(MerchantRule).where(
                MerchantRule.profile_id == profile_id,
                MerchantRule.match_type == "exact",
            )
        )
    }
    created = 0
    updated = 0
    for key, counter in votes.items():
        category_id = counter.most_common(1)[0][0]
        rule = existing.get(key)
        if rule is None:
            session.add(
                MerchantRule(
                    profile_id=profile_id,
                    category_id=category_id,
                    pattern=key,
                    match_type="exact",
                    hit_count=sum(counter.values()),
                )
            )
            created += 1
        elif rule.category_id != category_id:
            rule.category_id = category_id
            rule.is_active = True
            updated += 1
    session.flush()
    return created, updated


def seed_default_merchant_rules(session: Session, profile_id: int) -> int:
    """Seed generic brand rules mapped to the profile's default categories."""

    slugs = {
        category.slug: category.id
        for category in session.scalars(
            select(Category).where(Category.profile_id == profile_id)
        )
    }
    existing = {
        (rule.pattern, rule.match_type)
        for rule in session.scalars(
            select(MerchantRule).where(MerchantRule.profile_id == profile_id)
        )
    }
    created = 0
    for keyword, slug in DEFAULT_MERCHANT_RULES:
        category_id = slugs.get(slug)
        pattern = keyword.upper()
        if category_id is None or (pattern, "contains") in existing:
            continue
        session.add(
            MerchantRule(
                profile_id=profile_id,
                category_id=category_id,
                pattern=pattern,
                match_type="contains",
                is_default=True,
            )
        )
        created += 1
    if created:
        session.flush()
    return created


# -- CRUD -------------------------------------------------------------------
def list_merchant_rules(session: Session, profile_id: int) -> list[MerchantRule]:
    require_profile(session, profile_id)
    return list(
        session.scalars(
            select(MerchantRule)
            .where(MerchantRule.profile_id == profile_id)
            .order_by(
                MerchantRule.is_active.desc(),
                MerchantRule.hit_count.desc(),
                MerchantRule.pattern,
            )
        )
    )


def create_merchant_rule(
    session: Session, profile_id: int, values: MerchantRuleCreate
) -> MerchantRule:
    require_profile(session, profile_id)
    _require_category(session, profile_id, values.category_id)
    pattern = _normalize_pattern(values.pattern, values.match_type)
    rule = MerchantRule(
        profile_id=profile_id,
        category_id=values.category_id,
        pattern=pattern,
        match_type=values.match_type,
    )
    session.add(rule)
    session.flush()
    return rule


def require_merchant_rule(session: Session, profile_id: int, rule_id: int) -> MerchantRule:
    rule = session.scalar(
        select(MerchantRule).where(
            MerchantRule.id == rule_id, MerchantRule.profile_id == profile_id
        )
    )
    if rule is None:
        raise ResourceNotFoundError("merchant rule not found")
    return rule


def update_merchant_rule(
    session: Session, profile_id: int, rule_id: int, values: MerchantRuleUpdate
) -> MerchantRule:
    rule = require_merchant_rule(session, profile_id, rule_id)
    changes = values.model_dump(exclude_unset=True)
    for field in ("pattern", "category_id", "match_type"):
        if field in changes and changes[field] is None:
            raise InvalidUpdateError(f"required fields cannot be null: {field}")
    if "category_id" in changes:
        _require_category(session, profile_id, int(changes["category_id"]))
    match_type = changes.get("match_type", rule.match_type)
    if "pattern" in changes:
        changes["pattern"] = _normalize_pattern(str(changes["pattern"]), match_type)
    for field, value in changes.items():
        setattr(rule, field, value)
    session.flush()
    return rule


def delete_merchant_rule(session: Session, profile_id: int, rule_id: int) -> None:
    rule = require_merchant_rule(session, profile_id, rule_id)
    session.delete(rule)
    session.flush()


def _normalize_pattern(pattern: str, match_type: str) -> str:
    if match_type == "exact":
        return normalize_merchant_key(pattern, pattern)
    return normalize_search_text(pattern, "")


def _require_category(session: Session, profile_id: int, category_id: int) -> None:
    exists = session.scalar(
        select(Category.id).where(
            Category.id == category_id, Category.profile_id == profile_id
        )
    )
    if exists is None:
        raise ResourceNotFoundError("category not found")
