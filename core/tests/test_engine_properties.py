"""Hypothesis property tests for the scoring engine.

These don't replace the golden fixtures — they check invariants that must
hold for EVERY input, not just the hand-picked cases: money is conserved,
the winner never pays, and the engine is a pure/deterministic function.
"""

from __future__ import annotations

from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st
from taidi_core.models import GameRules
from taidi_core.rules import compute_card_transfers

PLAYER_IDS = [uuid4() for _ in range(6)]


@st.composite
def card_counts_and_rules(draw):
    n = draw(st.integers(min_value=2, max_value=6))
    players = PLAYER_IDS[:n]
    winner = draw(st.sampled_from(players))
    counts = {winner: 0}
    for p in players:
        if p != winner:
            counts[p] = draw(st.integers(min_value=1, max_value=51))

    double = draw(st.integers(min_value=1, max_value=40))
    triple = draw(st.integers(min_value=double, max_value=52))
    rules = GameRules(
        card_value_cents=draw(st.integers(min_value=0, max_value=500)),
        base_cards=draw(st.integers(min_value=0, max_value=10)),
        multipliers_enabled=draw(st.booleans()),
        double_threshold=double,
        triple_threshold=triple,
        difference_payouts=draw(st.booleans()),
    )
    return counts, rules


@given(data=card_counts_and_rules())
@settings(max_examples=200)
def test_round_is_always_zero_sum(data):
    card_counts, rules = data
    transfers, winner = compute_card_transfers(card_counts, rules, round_no=1)
    net = dict.fromkeys(card_counts, 0)
    for t in transfers:
        net[t.from_player] -= t.amount_cents
        net[t.to_player] += t.amount_cents
    assert sum(net.values()) == 0


@given(data=card_counts_and_rules())
@settings(max_examples=200)
def test_winner_never_pays(data):
    card_counts, rules = data
    transfers, winner = compute_card_transfers(card_counts, rules, round_no=1)
    assert all(t.from_player != winner for t in transfers)


@given(data=card_counts_and_rules())
@settings(max_examples=100)
def test_deterministic(data):
    card_counts, rules = data
    t1, w1 = compute_card_transfers(card_counts, rules, round_no=1)
    t2, w2 = compute_card_transfers(card_counts, rules, round_no=1)
    assert w1 == w2
    assert t1 == t2


@given(data=card_counts_and_rules())
@settings(max_examples=200)
def test_all_amounts_non_negative(data):
    card_counts, rules = data
    transfers, _ = compute_card_transfers(card_counts, rules, round_no=1)
    assert all(t.amount_cents >= 0 for t in transfers)
