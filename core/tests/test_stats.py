"""Lifetime stats derived from ended rooms."""

from __future__ import annotations

from uuid import uuid4

from taidi_core import machine
from taidi_core.models import GameRules, RoomState
from taidi_core.stats import player_lifetime_stats


def _ended_room(now, winner_delta=100):
    A, B = uuid4(), uuid4()
    state = RoomState.new(room_id=uuid4(), host_id=A, host_display_name="Alice", now=now)
    state = machine.fold(
        state,
        machine.join_player(
            state, expected_seq=state.seq, player_id=B, display_name="Bob", now=now
        ),
    )
    state = machine.fold(
        state,
        machine.start_game(
            state,
            expected_seq=state.seq,
            actor=A,
            rules=GameRules(card_value_cents=winner_delta),
            now=now,
        ),
    )
    state = machine.fold(state, machine.claim_win(state, expected_seq=state.seq, actor=A, now=now))
    state = machine.fold(
        state, machine.submit_cards(state, expected_seq=state.seq, actor=B, cards=1, now=now)
    )
    state = machine.fold(state, machine.end_game(state, expected_seq=state.seq, actor=A, now=now))
    return state, A, B


def test_stats_ignore_unended_rooms(now):
    state, A, B = _ended_room(now)
    lobby_only = RoomState.new(room_id=uuid4(), host_id=uuid4(), host_display_name="X", now=now)
    stats = player_lifetime_stats([state, lobby_only])
    assert set(stats) == {A, B}


def test_stats_accumulate_across_games(now):
    room1, A, B = _ended_room(now, winner_delta=100)
    stats = player_lifetime_stats([room1, room1])
    assert stats[A].games == 2
    assert stats[A].wins == 2
    assert stats[B].losses == 2
    assert stats[A].total_cents == room1.balances[A] * 2
    assert stats[A].avg_cents == room1.balances[A]


def test_win_loss_tie_classification(now):
    state, A, B = _ended_room(now)
    stats = player_lifetime_stats([state])
    assert stats[A].wins == 1 and stats[A].losses == 0 and stats[A].ties == 0
    assert stats[B].losses == 1
