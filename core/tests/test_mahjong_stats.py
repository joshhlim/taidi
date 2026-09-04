"""Lifetime stats derived from ended Mahjong rooms."""

from __future__ import annotations

from uuid import uuid4

from mahjong_core import machine
from mahjong_core.models import MahjongRules, RoomState
from mahjong_core.stats import player_lifetime_stats


def _ended_room(now, yao_delta=100):
    A, B, C, D = uuid4(), uuid4(), uuid4(), uuid4()
    state = RoomState.new(room_id=uuid4(), host_id=A, host_display_name="Alice", now=now)
    for pid, name in [(B, "Bob"), (C, "Cara"), (D, "Dan")]:
        state = machine.fold(
            state,
            machine.join_player(
                state, expected_seq=state.seq, player_id=pid, display_name=name, now=now
            ),
        )
    state = machine.fold(
        state,
        machine.start_game(
            state,
            expected_seq=state.seq,
            actor=A,
            rules=MahjongRules(yao_chips=yao_delta),
            now=now,
        ),
    )
    state = machine.fold(
        state,
        machine.declare_yao(
            state, expected_seq=state.seq, actor=A, target_seat=1, an=False, now=now
        ),
    )
    state = machine.fold(state, machine.end_game(state, expected_seq=state.seq, actor=A, now=now))
    return state, A, B, C, D


def test_stats_ignore_unended_rooms(now):
    state, A, B, C, D = _ended_room(now)
    lobby_only = RoomState.new(room_id=uuid4(), host_id=uuid4(), host_display_name="X", now=now)
    stats = player_lifetime_stats([state, lobby_only])
    assert set(stats) == {A, B, C, D}


def test_stats_accumulate_across_games(now):
    room1, A, B, C, D = _ended_room(now, yao_delta=100)
    stats = player_lifetime_stats([room1, room1])
    assert stats[A].games == 2
    assert stats[A].wins == 2
    assert stats[B].losses == 2
    assert stats[A].total_cents == room1.balances[A] * 2
    assert stats[A].avg_cents == room1.balances[A]


def test_win_loss_tie_classification(now):
    state, A, B, C, D = _ended_room(now)
    stats = player_lifetime_stats([state])
    assert stats[A].wins == 1 and stats[A].losses == 0 and stats[A].ties == 0
    assert stats[B].losses == 1
    assert stats[C].ties == 1 and stats[D].ties == 1
