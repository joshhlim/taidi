"""Hypothesis property tests for the Mahjong settlement math.

These don't replace the fixed-case tests in test_mahjong_machine.py — they
check invariants that must hold for EVERY input, not just hand-picked
cases: the amount collected always matches the settlement-table formula,
the actor never pays themselves, and every other player's balance only
ever moves toward the actor, never away.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from mahjong_core import machine
from mahjong_core.models import MahjongRules, RoomState

from .conftest import letter_id

A, B, C, D = letter_id("mp-A"), letter_id("mp-B"), letter_id("mp-C"), letter_id("mp-D")
SEATS = [A, B, C, D]

NOW = __import__("datetime").datetime(2026, 9, 1, tzinfo=__import__("datetime").UTC)


@st.composite
def mahjong_rules(draw):
    return MahjongRules(
        yao_unit_cents=draw(st.integers(min_value=0, max_value=2000)),
        gang_unit_cents=draw(st.integers(min_value=0, max_value=2000)),
        tai_unit_cents=draw(st.integers(min_value=0, max_value=2000)),
        zimo_unit_cents=draw(st.integers(min_value=0, max_value=2000)),
        max_tai=draw(st.integers(min_value=1, max_value=20)),
    )


def _started_room(rules: MahjongRules) -> RoomState:
    state = RoomState.new(room_id=A, host_id=A, host_display_name="A", now=NOW)
    for pid, name in [(B, "B"), (C, "C"), (D, "D")]:
        state = machine.fold(
            state,
            machine.join_player(
                state, expected_seq=state.seq, player_id=pid, display_name=name, now=NOW
            ),
        )
    return machine.fold(
        state, machine.start_game(state, expected_seq=state.seq, actor=A, rules=rules, now=NOW)
    )


def _others_never_gain(before: RoomState, after: RoomState, actor) -> bool:
    return all(after.balances[p] <= before.balances[p] for p in SEATS if p != actor)


@given(
    rules=mahjong_rules(),
    actor_idx=st.integers(0, 3),
    target_idx=st.integers(0, 3),
    an=st.booleans(),
)
@settings(max_examples=200)
def test_yao_matches_formula(rules, actor_idx, target_idx, an):
    state = _started_room(rules)
    actor, target = SEATS[actor_idx], SEATS[target_idx]
    before = state
    after = machine.fold(
        state,
        machine.declare_yao(
            state, expected_seq=state.seq, actor=actor, target_seat=target_idx, an=an, now=NOW
        ),
    )
    unit = rules.yao_unit_cents * (2 if an else 1)
    expected_total = unit * 3 if target == actor else unit
    assert after.balances[actor] - before.balances[actor] == expected_total
    assert _others_never_gain(before, after, actor)


@given(
    rules=mahjong_rules(),
    actor_idx=st.integers(0, 3),
    target=st.one_of(st.integers(0, 3), st.just("angang")),
)
@settings(max_examples=200)
def test_gang_matches_formula(rules, actor_idx, target):
    state = _started_room(rules)
    actor = SEATS[actor_idx]
    before = state
    after = machine.fold(
        state,
        machine.declare_gang(state, expected_seq=state.seq, actor=actor, target=target, now=NOW),
    )
    if target == "angang":
        expected_total = rules.gang_unit_cents * 2 * 3
    elif SEATS[target] == actor:
        expected_total = rules.gang_unit_cents * 1 * 3
    else:
        expected_total = rules.gang_unit_cents * 3
    assert after.balances[actor] - before.balances[actor] == expected_total
    assert _others_never_gain(before, after, actor)
    assert after.hands[0].had_gang


@given(rules=mahjong_rules(), actor_idx=st.integers(0, 3), tai=st.integers(1, 20))
@settings(max_examples=200)
def test_zimo_matches_formula(rules, actor_idx, tai):
    tai = 1 + tai % rules.max_tai
    state = _started_room(rules)
    actor = SEATS[actor_idx]
    before = state
    after = machine.fold(
        state,
        machine.declare_hu(
            state,
            expected_seq=state.seq,
            actor=actor,
            mode="zimo",
            target_seat=None,
            tai=tai,
            now=NOW,
        ),
    )
    assert after.balances[actor] - before.balances[actor] == rules.zimo_unit_cents * tai * 3
    assert _others_never_gain(before, after, actor)


@given(
    rules=mahjong_rules(),
    actor_idx=st.integers(0, 3),
    target_offset=st.integers(1, 3),
    tai=st.integers(1, 20),
)
@settings(max_examples=200)
def test_direct_hu_matches_formula(rules, actor_idx, target_offset, tai):
    tai = 1 + tai % rules.max_tai
    target_idx = (actor_idx + target_offset) % 4
    state = _started_room(rules)
    actor, target = SEATS[actor_idx], SEATS[target_idx]
    before = state
    after = machine.fold(
        state,
        machine.declare_hu(
            state,
            expected_seq=state.seq,
            actor=actor,
            mode="direct",
            target_seat=target_idx,
            tai=tai,
            now=NOW,
        ),
    )
    assert after.balances[actor] - before.balances[actor] == rules.tai_unit_cents * tai
    assert before.balances[target] - after.balances[target] == rules.tai_unit_cents * tai
    assert _others_never_gain(before, after, actor)


@given(
    rules=mahjong_rules(),
    actor_idx=st.integers(0, 3),
    target_offset=st.integers(1, 3),
    tai=st.integers(1, 20),
)
@settings(max_examples=200)
def test_bao_charges_full_zimo_total_to_one_player(rules, actor_idx, target_offset, tai):
    tai = 1 + tai % rules.max_tai
    target_idx = (actor_idx + target_offset) % 4
    state = _started_room(rules)
    actor, target = SEATS[actor_idx], SEATS[target_idx]
    before = state
    after = machine.fold(
        state,
        machine.declare_hu(
            state,
            expected_seq=state.seq,
            actor=actor,
            mode="bao",
            target_seat=target_idx,
            tai=tai,
            now=NOW,
        ),
    )
    expected = rules.zimo_unit_cents * tai * 3
    assert after.balances[actor] - before.balances[actor] == expected
    assert before.balances[target] - after.balances[target] == expected
    assert _others_never_gain(before, after, actor)


@given(
    rules=mahjong_rules(),
    actor_idx=st.integers(0, 3),
    target_idx=st.integers(0, 3),
    an=st.booleans(),
)
@settings(max_examples=100)
def test_yao_is_always_zero_sum(rules, actor_idx, target_idx, an):
    state = _started_room(rules)
    actor = SEATS[actor_idx]
    after = machine.fold(
        state,
        machine.declare_yao(
            state, expected_seq=state.seq, actor=actor, target_seat=target_idx, an=an, now=NOW
        ),
    )
    assert sum(after.balances.values()) == sum(state.balances.values()) == 0
