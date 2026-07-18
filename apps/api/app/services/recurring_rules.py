"""Pure, persistence-free recurring-charge detection (product plan §12.1).

Kept free of ORM/session state so the heuristics can be unit-tested in isolation
and reused by the recurring service. Money is integer cents throughout.

The detector groups a profile's spending transactions by a normalized merchant
key and reports groups that repeat on a recognisable cadence with stable-enough
amounts. Irregular frequent merchants (groceries, restaurants) do not map to a
clean cadence and are therefore excluded, per §12.1.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Literal

Cadence = Literal["weekly", "biweekly", "monthly", "quarterly", "annual"]
Confidence = Literal["high", "medium", "low"]

# (name, target interval in days, ± tolerance in days)
_CADENCES: tuple[tuple[Cadence, int, int], ...] = (
    ("weekly", 7, 2),
    ("biweekly", 14, 3),
    ("monthly", 30, 6),
    ("quarterly", 91, 12),
    ("annual", 365, 25),
)
_CADENCE_TARGET: dict[Cadence, int] = {name: target for name, target, _ in _CADENCES}
_CADENCE_TARGET_TOL: dict[Cadence, int] = {name: tol for name, _, tol in _CADENCES}

# Amounts within the larger of these tolerances are treated as "the same" charge
# for the purpose of a *high-confidence* series. Recurring charges are generally
# close in amount, so this is deliberately tight.
_AMOUNT_ABS_TOLERANCE_CENTS = 150
_AMOUNT_PCT_TOLERANCE = 0.10

# Splitting a merchant's charges into amount clusters separates genuinely distinct
# recurring prices (e.g. two subscriptions billed by the same processor) while the
# percentage term keeps naturally-variable bills (utilities) in one cluster. A
# cluster break happens only when an amount jumps more than the larger tolerance.
_AMOUNT_SPLIT_ABS_CENTS = 300
_AMOUNT_SPLIT_PCT = 0.35

_MIN_INTERVAL_DAYS = 5  # more frequent than weekly is not a subscription cadence


@dataclass(frozen=True, slots=True)
class RecurringObservation:
    """One transaction fact fed to the detector."""

    transaction_id: int
    txn_date: date
    merchant: str
    raw_description: str
    amount_cents: int
    category_id: int | None = None
    account_id: int | None = None


@dataclass(frozen=True, slots=True)
class DetectedSeries:
    """A detected recurring series, before persistence."""

    merchant_key: str
    display_name: str
    amount_cents: int
    amount_min_cents: int
    amount_max_cents: int
    cadence: Cadence
    interval_days: int
    confidence: Confidence
    occurrence_count: int
    first_charge_date: date
    last_charge_date: date
    next_expected_date: date
    category_id: int | None
    account_id: int | None
    rationale: str
    transaction_ids: tuple[int, ...] = field(default_factory=tuple)


def normalize_merchant(merchant: str, raw_description: str) -> str:
    """Return a stable merchant key: letters only, collapsed, first four tokens.

    Store numbers, reference ids, and punctuation are dropped so the same
    merchant matches across statements, while distinct merchants stay separate.
    """

    base = (merchant or raw_description or "").upper()
    base = re.sub(r"[^A-Z ]+", " ", base)
    tokens = base.split()
    return " ".join(tokens[:4])


def _classify_interval(days: float) -> tuple[Cadence, int] | None:
    for name, target, tolerance in _CADENCES:
        if abs(days - target) <= tolerance:
            return name, target
    return None


def _most_common(values: list[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    counts: dict[int, int] = defaultdict(int)
    for value in present:
        counts[value] += 1
    # Deterministic: highest count, then smallest id.
    return min(counts, key=lambda key: (-counts[key], key))


def _amounts_are_stable(amounts: list[int]) -> bool:
    median = statistics.median(amounts)
    tolerance = max(_AMOUNT_ABS_TOLERANCE_CENTS, int(abs(median) * _AMOUNT_PCT_TOLERANCE))
    return all(abs(amount - median) <= tolerance for amount in amounts)


def _split_by_amount(
    observations: list[RecurringObservation],
) -> list[list[RecurringObservation]]:
    """Partition a merchant's charges into clusters of similar amount.

    Charges are sorted by amount and a new cluster starts wherever the jump from
    the previous amount exceeds the larger of the absolute/percentage tolerance.
    Naturally-variable bills stay in one cluster; two distinct fixed prices split.
    """

    ordered = sorted(observations, key=lambda o: (o.amount_cents, o.transaction_id))
    clusters: list[list[RecurringObservation]] = [[ordered[0]]]
    for previous, current in zip(ordered, ordered[1:], strict=False):
        threshold = max(
            _AMOUNT_SPLIT_ABS_CENTS,
            int(abs(previous.amount_cents) * _AMOUNT_SPLIT_PCT),
        )
        if abs(current.amount_cents - previous.amount_cents) > threshold:
            clusters.append([current])
        else:
            clusters[-1].append(current)
    return clusters


def _detect_group(observations: list[RecurringObservation]) -> list[DetectedSeries]:
    """Detect recurring series within one merchant group.

    Distinct amount clusters are each considered a candidate series; if none
    qualify, the whole group is retried so variable-amount bills (utilities) whose
    amounts scatter across clusters are still detected as a single series.
    """

    clusters = _split_by_amount(observations)
    if len(clusters) > 1:
        # A split cluster must be well-attested (>= 3 charges): splitting can make a
        # clean cadence appear in two noisy charges by chance, so a mere pair from a
        # split is not enough to call it recurring.
        detected = [
            series
            for cluster in clusters
            if (series := _detect_cluster(cluster)) is not None
            and series.occurrence_count >= 3
        ]
        if len(detected) == 1:
            return detected  # keep the plain merchant key for stable matching
        if detected:
            # Several priced series at one merchant: suffix each key with its amount
            # so the profile/merchant-key unique constraint holds and re-runs match.
            return [
                replace(s, merchant_key=f"{s.merchant_key}#{s.amount_cents}")
                for s in detected
            ]
    # Single amount cluster, or a split that found no well-attested series: detect
    # over the whole group so variable-amount bills (utilities) are still caught.
    whole = _detect_cluster(observations)
    return [whole] if whole is not None else []


def _detect_cluster(observations: list[RecurringObservation]) -> DetectedSeries | None:
    ordered = sorted(observations, key=lambda o: (o.txn_date, o.transaction_id))
    if len(ordered) < 2:
        return None
    gaps = [
        (ordered[i].txn_date - ordered[i - 1].txn_date).days
        for i in range(1, len(ordered))
    ]
    gaps = [gap for gap in gaps if gap > 0]
    if not gaps:
        return None
    median_gap = statistics.median(gaps)
    if median_gap < _MIN_INTERVAL_DAYS:
        return None
    classified = _classify_interval(median_gap)
    if classified is None:
        return None
    cadence, target = classified

    # Every gap must be within half a period of the cadence target, which
    # excludes irregular frequent merchants that happen to average a cadence.
    window = max(target // 2, _CADENCE_TARGET_TOL[cadence])
    if not all(abs(gap - target) <= window for gap in gaps):
        return None

    amounts = [o.amount_cents for o in ordered]
    stable = _amounts_are_stable(amounts)
    occurrences = len(ordered)
    within_tolerance = sum(abs(gap - target) <= _CADENCE_TARGET_TOL[cadence] for gap in gaps)

    if occurrences >= 3 and within_tolerance == len(gaps) and stable:
        confidence: Confidence = "high"
    elif occurrences >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    representative = int(statistics.median(amounts))
    last = ordered[-1]
    interval_days = int(round(statistics.mean(gaps)))
    next_expected = last.txn_date + timedelta(days=interval_days)
    rationale = (
        f"{occurrences} charges ~{interval_days} days apart"
        f"{'' if stable else ' with varying amounts'}; matched on merchant "
        f"'{normalize_merchant(last.merchant, last.raw_description)}'."
    )
    return DetectedSeries(
        merchant_key=normalize_merchant(last.merchant, last.raw_description),
        display_name=(last.merchant or last.raw_description).strip(),
        amount_cents=representative,
        amount_min_cents=min(amounts),
        amount_max_cents=max(amounts),
        cadence=cadence,
        interval_days=interval_days,
        confidence=confidence,
        occurrence_count=occurrences,
        first_charge_date=ordered[0].txn_date,
        last_charge_date=last.txn_date,
        next_expected_date=next_expected,
        category_id=_most_common([o.category_id for o in ordered]),
        account_id=_most_common([o.account_id for o in ordered]),
        rationale=rationale,
        transaction_ids=tuple(o.transaction_id for o in ordered),
    )


def detect_recurring_series(
    observations: list[RecurringObservation],
) -> list[DetectedSeries]:
    """Group observations by merchant and return detected recurring series.

    Results are ordered by soonest next-expected date, then merchant key, so
    persistence and API output are deterministic.
    """

    groups: dict[str, list[RecurringObservation]] = defaultdict(list)
    for observation in observations:
        key = normalize_merchant(observation.merchant, observation.raw_description)
        if key:
            groups[key].append(observation)

    detected: list[DetectedSeries] = []
    for group in groups.values():
        detected.extend(_detect_group(group))
    detected.sort(key=lambda s: (s.next_expected_date, s.merchant_key))
    return detected
