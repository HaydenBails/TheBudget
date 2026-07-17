"""Typed profile-isolated merchant auto-categorization rule endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    MerchantRuleApplyResult,
    MerchantRuleCreate,
    MerchantRuleLearnResult,
    MerchantRuleRead,
    MerchantRuleUpdate,
)
from app.services import (
    apply_rules_to_uncategorized,
    create_merchant_rule,
    delete_merchant_rule,
    learn_from_history,
    list_merchant_rules,
    require_merchant_rule,
    update_merchant_rule,
)

router = APIRouter(prefix="/profiles/{profile_id}/merchant-rules", tags=["merchant-rules"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[MerchantRuleRead])
def get_merchant_rules(profile_id: int, session: SessionDependency):
    """List merchant rules for one profile."""

    return list_merchant_rules(session, profile_id)


@router.post("", response_model=MerchantRuleRead, status_code=status.HTTP_201_CREATED)
def post_merchant_rule(profile_id: int, values: MerchantRuleCreate, session: SessionDependency):
    """Create a merchant rule owned by the path profile."""

    return create_merchant_rule(session, profile_id, values)


@router.post("/apply", response_model=MerchantRuleApplyResult)
def post_apply_rules(profile_id: int, session: SessionDependency):
    """Auto-categorize every uncategorized transaction that a rule matches."""

    return MerchantRuleApplyResult(categorized=apply_rules_to_uncategorized(session, profile_id))


@router.post("/learn", response_model=MerchantRuleLearnResult)
def post_learn_rules(profile_id: int, session: SessionDependency):
    """Learn rules from already-categorized transactions (majority category)."""

    created, updated = learn_from_history(session, profile_id)
    return MerchantRuleLearnResult(created=created, updated=updated)


@router.patch("/{rule_id}", response_model=MerchantRuleRead)
def patch_merchant_rule(
    profile_id: int, rule_id: int, values: MerchantRuleUpdate, session: SessionDependency
):
    """Update a merchant rule within its owning profile."""

    return update_merchant_rule(session, profile_id, rule_id, values)


@router.get("/{rule_id}", response_model=MerchantRuleRead)
def get_merchant_rule(profile_id: int, rule_id: int, session: SessionDependency):
    """Get a merchant rule within its owning profile."""

    return require_merchant_rule(session, profile_id, rule_id)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant_rule_route(profile_id: int, rule_id: int, session: SessionDependency):
    """Remove a merchant rule within its owning profile."""

    delete_merchant_rule(session, profile_id, rule_id)
