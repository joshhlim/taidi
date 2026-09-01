"""Golden fixtures: compute_card_transfers against every rule-toggle combination.

Each case is (card_counts by letter, rules, expected total cents paid BY each
letter). Amounts are hand-computed from the rule definitions, independent of
the implementation under test.
"""

from __future__ import annotations

import pytest
from taidi_core.models import GameRules, TransferKind
from taidi_core.rules import compute_card_transfers

from .conftest import letter_id


def _paid(transfers, letter: str, kind: TransferKind | None = None) -> int:
    pid = letter_id(letter)
    return sum(
        t.amount_cents
        for t in transfers
        if t.from_player == pid and (kind is None or t.kind == kind)
    )


def _by_letters(counts: dict[str, int]) -> dict:
    return {letter_id(k): v for k, v in counts.items()}


CASES = [
    pytest.param(
        {"A": 0, "B": 3, "C": 11, "D": 14},
        GameRules(card_value_cents=100),
        {"A": 0, "B": 500, "C": 4000, "D": 8600},
        id="default-rules-4p",
    ),
    pytest.param(
        {"A": 0, "B": 3, "C": 11, "D": 14},
        GameRules(card_value_cents=100, multipliers_enabled=False),
        {"A": 0, "B": 500, "C": 2100, "D": 3000},
        id="multipliers-disabled",
    ),
    pytest.param(
        {"A": 0, "B": 11, "C": 12, "D": 15},
        GameRules(
            card_value_cents=100,
            double_threshold=12,
            triple_threshold=15,
            difference_payouts=False,
            base_cards=0,
        ),
        {"A": 0, "B": 1100, "C": 2400, "D": 4500},
        id="custom-thresholds-winner-only",
    ),
    pytest.param(
        {"A": 0, "B": 4},
        GameRules(
            card_value_cents=50, base_cards=5, multipliers_enabled=False, difference_payouts=False
        ),
        {"A": 0, "B": 450},
        id="configurable-base",
    ),
]


@pytest.mark.parametrize("card_counts,rules,expected_paid_cents", CASES)
def test_total_paid_per_player(card_counts, rules, expected_paid_cents):
    transfers, winner = compute_card_transfers(_by_letters(card_counts), rules, round_no=1)
    assert winner == letter_id("A")
    for letter, expected in expected_paid_cents.items():
        assert _paid(transfers, letter) == expected, f"{letter} paid wrong total"


def test_default_rules_are_zero_sum():
    rules = GameRules(card_value_cents=100)
    transfers, winner = compute_card_transfers(
        _by_letters({"A": 0, "B": 3, "C": 11, "D": 14}), rules, 1
    )
    net: dict = {}
    for t in transfers:
        net[t.from_player] = net.get(t.from_player, 0) - t.amount_cents
        net[t.to_player] = net.get(t.to_player, 0) + t.amount_cents
    assert sum(net.values()) == 0


@pytest.mark.parametrize("counts", [{"A": 1, "B": 2, "C": 3}, {"A": 0, "B": 0, "C": 5}])
def test_exactly_one_winner_required(counts):
    with pytest.raises(ValueError):
        compute_card_transfers(_by_letters(counts), GameRules(), round_no=1)
