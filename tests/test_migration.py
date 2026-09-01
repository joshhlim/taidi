"""Migrating legacy Streamlit archives into taidi_core rooms.

Builds realistic archive entries with the ACTUAL legacy scoring engine
(game.py), migrates them, and checks the replayed room's balances match the
original archived totals to within float-accumulation tolerance.
"""

from __future__ import annotations

from migrate_legacy_to_events import BALANCE_TOLERANCE_CENTS, migrate_archive_entry
from taidi_core.models import RoomStatus

import db
from game import CardGameTracker
from game import GameRules as LegacyGameRules


def _legacy_archive_entry(players, rounds, rules=None, special_hands=None):
    """rounds: list of card_counts_list (in player order). special_hands: list of dicts per round."""
    tracker = CardGameTracker(players, rules or LegacyGameRules())
    for i, counts in enumerate(rounds):
        specials = special_hands[i] if special_hands else None
        tracker.play_round(counts, special_hand_counts=specials)
    return {
        "archive_id": "legacy-1",
        "created_at": "2026-06-15 20:30:00",
        "players": tracker.players,
        "rounds_played": tracker.rounds_played,
        "rules": tracker.rules.to_dict(),
        "final_totals": {p: float(v) for p, v in tracker.balances.items()},
        "tx_log": tracker.tx_log,
    }


def test_migrates_a_simple_multi_round_game():
    entry = _legacy_archive_entry(
        ["Alice", "Bob", "Charlie", "Dana"],
        rounds=[[0, 3, 11, 14], [5, 0, 2, 8], [1, 6, 0, 9]],
    )
    result = migrate_archive_entry(entry)
    assert result.room.status == RoomStatus.ENDED
    assert result.max_balance_drift_cents <= BALANCE_TOLERANCE_CENTS
    assert not result.warnings
    assert sum(result.room.balances.values()) == 0
    assert len(result.room.rounds) == 3


def test_migrates_a_game_with_special_hands():
    entry = _legacy_archive_entry(
        ["Alice", "Bob", "Charlie"],
        rounds=[[0, 3, 11], [4, 0, 2]],
        special_hands=[{"Bob": 2}, None],
    )
    result = migrate_archive_entry(entry)
    assert result.max_balance_drift_cents <= BALANCE_TOLERANCE_CENTS
    assert not result.warnings
    # Bob's 2 special-hand claims in round 1 should have been replayed as 2 discrete events
    special_events = [e for e in result.events if e.type.value == "special_hand"]
    assert len(special_events) == 2


def test_migrates_with_custom_rules():
    rules = LegacyGameRules(
        card_value=0.5,
        base_cards=0,
        multipliers_enabled=False,
        difference_payouts=False,
    )
    entry = _legacy_archive_entry(["Alice", "Bob", "Charlie"], rounds=[[0, 7, 20]], rules=rules)
    result = migrate_archive_entry(entry)
    assert result.max_balance_drift_cents <= BALANCE_TOLERANCE_CENTS
    assert result.room.rules is not None
    assert result.room.rules.card_value_cents == 50
    assert result.room.rules.multipliers_enabled is False


def test_full_database_migration_reports_all_games():
    entry1 = _legacy_archive_entry(["Alice", "Bob"], rounds=[[0, 5], [3, 0]])
    entry2 = _legacy_archive_entry(["Charlie", "Dana", "Eve"], rounds=[[0, 4, 9]])
    db.archive_add(entry1)
    db.archive_add(entry2)

    for entry in db.archive_all():
        result = migrate_archive_entry(entry)
        assert result.max_balance_drift_cents <= BALANCE_TOLERANCE_CENTS
        assert not result.warnings
