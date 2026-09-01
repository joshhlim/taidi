#!/usr/bin/env python3
"""Migrate finished games from the legacy Streamlit app (db.py) into taidi_core
rooms, verifying the replayed balances match the original archived totals.

Scope: only ARCHIVED (finished) games are migrated. Active/unfinished
Streamlit sessions don't map onto the room model (no host, no join events,
no live players) and are expected to just be replayed as fresh rooms in the
new app instead.

Player identity: each legacy player NAME gets a fresh UUID for this replay.
Reconciling that with real user accounts is Phase 2/3 scope (a guest player
claimed by a signed-up user), not this script's job — this script only
proves the event log reproduces the original money.

Reconstruction: legacy archives store computed transfers, not raw card
counts, but the counts are recoverable from them — every non-winner has one
"cards"-kind transfer to the winner whose `cards` field IS their card count
for that round, and every "special"-kind transfer's `cards` field divided by
`special_hand_cards` gives the claim count for that (round, claimer).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))

from taidi_core import machine  # noqa: E402
from taidi_core.models import GameRules, RoomState  # noqa: E402

import db  # noqa: E402

BALANCE_TOLERANCE_CENTS = 2  # legacy float accumulation can be off by a cent or two


@dataclass
class MigrationResult:
    archive_id: str
    room: RoomState
    events: list
    max_balance_drift_cents: int
    warnings: list[str]


def _parse_legacy_created_at(value: str | None) -> datetime:
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.now()


def _legacy_rules_to_core(legacy: dict) -> GameRules:
    return GameRules(
        card_value_cents=round(legacy.get("card_value", 0.20) * 100),
        base_cards=legacy.get("base_cards", 2),
        multipliers_enabled=legacy.get("multipliers_enabled", True),
        double_threshold=legacy.get("double_threshold", 10),
        triple_threshold=legacy.get("triple_threshold", 13),
        difference_payouts=legacy.get("difference_payouts", True),
        special_hands_enabled=legacy.get("special_hands_enabled", True),
        special_hand_cards=legacy.get("special_hand_cards", 5),
    )


def _reconstruct_round_cards(tx_record: dict, warnings: list[str]) -> dict[str, int]:
    """Recover {player_name: cards_left} for one legacy round from its stored transfers."""
    winner = tx_record["winner"]
    card_counts = {winner: 0}
    for t in tx_record.get("transfers", []):
        if t["kind"] == "cards":
            card_counts[t["from"]] = t["cards"]
    return card_counts, warnings


def _reconstruct_specials(tx_record: dict, special_hand_cards: int) -> dict[str, int]:
    """Recover {player_name: claim_count} for one legacy round's special-hand transfers.

    The legacy engine emits one transfer per (claimer, other payer), each
    repeating the SAME total `cards` value for that claimer's round — so we
    read it once per claimer, not sum it across payers.
    """
    totals: dict[str, int] = {}
    for t in tx_record.get("transfers", []):
        if t["kind"] == "special":
            totals[t["to"]] = t["cards"]
    if special_hand_cards <= 0:
        return {}
    return {name: cards // special_hand_cards for name, cards in totals.items()}


def migrate_archive_entry(entry: dict) -> MigrationResult:
    warnings: list[str] = []
    players: list[str] = entry.get("players", [])
    if len(players) < 2:
        raise ValueError(f"Archive {entry.get('archive_id')} has fewer than 2 players — skipping.")

    name_to_id: dict[str, UUID] = {name: uuid4() for name in players}
    host_id = name_to_id[players[0]]
    now = _parse_legacy_created_at(entry.get("created_at"))
    rules = _legacy_rules_to_core(entry.get("rules", {}))

    room_id = uuid4()
    state = RoomState.new(room_id=room_id, host_id=host_id, host_display_name=players[0], now=now)
    all_events = list(state.rounds)  # placeholder; real accumulation below
    all_events = []

    for name in players[1:]:
        ev = machine.join_player(
            state, expected_seq=state.seq, player_id=name_to_id[name], display_name=name, now=now
        )
        all_events += ev
        state = machine.fold(state, ev)

    ev = machine.start_game(state, expected_seq=state.seq, actor=host_id, rules=rules, now=now)
    all_events += ev
    state = machine.fold(state, ev)

    for tx_record in entry.get("tx_log", []):
        winner_name = tx_record["winner"]
        card_counts_by_name, warnings = _reconstruct_round_cards(tx_record, warnings)
        for name in players:
            if name not in card_counts_by_name:
                warnings.append(
                    f"{entry.get('archive_id')}: {name} missing from round {tx_record['round']!r}, defaulting to 0"
                )
                card_counts_by_name[name] = 0

        specials = _reconstruct_specials(tx_record, rules.special_hand_cards)

        ev = machine.claim_win(
            state, expected_seq=state.seq, actor=name_to_id[winner_name], now=now
        )
        all_events += ev
        state = machine.fold(state, ev)

        for name, cards in card_counts_by_name.items():
            if name == winner_name:
                continue
            ev = machine.submit_cards(
                state, expected_seq=state.seq, actor=name_to_id[name], cards=cards, now=now
            )
            all_events += ev
            state = machine.fold(state, ev)

        for name, count in specials.items():
            for _ in range(count):
                ev = machine.add_special_hand(
                    state, expected_seq=state.seq, actor=name_to_id[name], now=now
                )
                all_events += ev
                state = machine.fold(state, ev)

    ev = machine.end_game(state, expected_seq=state.seq, actor=host_id, now=now)
    all_events += ev
    state = machine.fold(state, ev)

    max_drift = 0
    for name, dollars in entry.get("final_totals", {}).items():
        pid = name_to_id.get(name)
        if pid is None:
            warnings.append(f"{entry.get('archive_id')}: final total for unknown player {name!r}")
            continue
        expected_cents = round(dollars * 100)
        actual_cents = state.balances.get(pid, 0)
        drift = abs(expected_cents - actual_cents)
        max_drift = max(max_drift, drift)
        if drift > BALANCE_TOLERANCE_CENTS:
            warnings.append(
                f"{entry.get('archive_id')}: {name} balance drift {drift}c "
                f"(expected {expected_cents}, got {actual_cents})"
            )

    return MigrationResult(
        archive_id=entry.get("archive_id", "?"),
        room=state,
        events=all_events,
        max_balance_drift_cents=max_drift,
        warnings=warnings,
    )


def main() -> int:
    db.init_db()
    archive = db.archive_all()
    if not archive:
        print("No archived games to migrate.")
        return 0

    ok, failed = 0, 0
    for entry in archive:
        try:
            result = migrate_archive_entry(entry)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {entry.get('archive_id', '?')}: {e}")
            failed += 1
            continue

        status = "OK" if result.max_balance_drift_cents <= BALANCE_TOLERANCE_CENTS else "DRIFT"
        print(
            f"{status:5s} {result.archive_id}  players={len(result.room.members)}  "
            f"rounds={len(result.room.rounds)}  events={len(result.events)}  "
            f"max_drift={result.max_balance_drift_cents}c"
        )
        for w in result.warnings:
            print(f"      ! {w}")
        ok += 1 if status == "OK" else 0
        failed += 1 if status != "OK" else 0

    print(f"\n{ok} verified, {failed} with issues, out of {len(archive)} archived games.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
