"""Scoring engine: payouts, rule toggles, snapshots, stats."""

import json

import pytest

from game import CardGameTracker, GameRules, compute_payouts, player_stats_df


def approx(a, b):
    assert abs(a - b) < 1e-9, f"{a} != {b}"


def test_default_rules_match_original_house_rules():
    # 4 players, $1/card. A wins; B=3, C=11 (x2), D=14 (x3). Base +2 each to winner.
    t = CardGameTracker(["A", "B", "C", "D"], GameRules(card_value=1.0))
    t.play_round([0, 3, 11, 14])
    approx(t.balances["A"], 3 + 11 * 2 + 14 * 3 + 6)
    approx(t.balances["B"], -(3 + 2) + (11 - 3) * 2 + (14 - 3) * 3)
    approx(t.balances["C"], -(11 * 2 + (11 - 3) * 2 + 2) + (14 - 11) * 3)
    approx(t.balances["D"], -(14 * 3 + (14 - 3) * 3 + (14 - 11) * 3 + 2))
    approx(sum(t.balances.values()), 0.0)


def test_multipliers_can_be_disabled():
    t = CardGameTracker(["A", "B", "C", "D"], GameRules(card_value=1.0, multipliers_enabled=False))
    t.play_round([0, 3, 11, 14])
    approx(t.balances["A"], 3 + 11 + 14 + 6)
    approx(sum(t.balances.values()), 0.0)


def test_custom_thresholds_and_winner_only_payouts():
    rules = GameRules(
        card_value=1.0,
        double_threshold=12,
        triple_threshold=15,
        difference_payouts=False,
        base_cards=0,
    )
    transfers, winner = compute_payouts({"A": 0, "B": 11, "C": 12, "D": 15}, rules)
    assert winner == "A"
    amounts = {t["from"]: t["amount"] for t in transfers}
    approx(amounts["B"], 11 * 1)
    approx(amounts["C"], 12 * 2)
    approx(amounts["D"], 15 * 3)
    assert all(t["to"] == "A" for t in transfers)


def test_configurable_base_payout():
    rules = GameRules(
        card_value=0.5, base_cards=5, multipliers_enabled=False, difference_payouts=False
    )
    t = CardGameTracker(["A", "B"], rules)
    t.play_round([0, 4])
    approx(t.balances["A"], (4 + 5) * 0.5)


def test_special_hands_bonus_and_toggle():
    rules = GameRules(card_value=1.0, special_hand_cards=7, base_cards=0, multipliers_enabled=False)
    t = CardGameTracker(["A", "B", "C"], rules)
    t.play_round([0, 1, 2], special_hand_counts={"B": 2})
    # B: +14 from A and C each, pays winner 1, receives diff 1 from C
    approx(t.balances["B"], 28 - 1 + 1)

    rules_off = GameRules(card_value=1.0, special_hands_enabled=False, base_cards=0)
    t2 = CardGameTracker(["A", "B", "C"], rules_off)
    t2.play_round([0, 1, 2], special_hand_counts={"B": 2})
    approx(t2.balances["B"], -1 + 1)


@pytest.mark.parametrize("counts", [[1, 2, 3], [0, 0, 5]])
def test_exactly_one_winner_required(counts):
    with pytest.raises(ValueError):
        compute_payouts(dict(zip(["A", "B", "C"], counts, strict=True)), GameRules())


def test_every_round_is_zero_sum_across_rule_combinations():
    for mult in (True, False):
        for diff in (True, False):
            for base in (0, 2):
                rules = GameRules(
                    multipliers_enabled=mult, difference_payouts=diff, base_cards=base
                )
                t = CardGameTracker(["A", "B", "C", "D"], rules)
                t.play_round([0, 3, 11, 14], special_hand_counts={"C": 1})
                t.play_round([7, 0, 1, 13])
                approx(sum(t.balances.values()), 0.0)


def test_snapshot_round_trip_through_json():
    t = CardGameTracker(["A", "B", "C", "D"], GameRules(card_value=0.2))
    t.play_round([0, 3, 11, 14])
    t.play_round([5, 0, 2, 8])
    snap = json.loads(json.dumps(t.to_snapshot()))
    t2 = CardGameTracker.from_snapshot(snap)
    assert t2.balances == t.balances
    assert t2.history.equals(t.history)
    assert t2.rules == t.rules
    assert len(t2.tx_log) == 2
    assert list(t2.get_summary().columns) == ["Round 1", "Round 2", "Total"]


def test_player_stats_derived_from_archive():
    archive = [
        {
            "created_at": "2026-01-01 20:00:00",
            "rounds_played": 3,
            "rules": {"card_value": 0.2},
            "final_totals": {"A": 5.0, "B": -5.0},
        },
        {
            "created_at": "2026-01-02 20:00:00",
            "rounds_played": 2,
            "rules": {"card_value": 0.5},
            "final_totals": {"A": -1.0, "B": 1.0, "C": 0.0},
        },
    ]
    stats = player_stats_df(archive)
    a = stats[stats["Player"] == "A"].iloc[0]
    assert a["Games"] == 2 and a["W"] == 1 and a["L"] == 1
    approx(a["Total"], 4.0)
    assert stats[stats["Player"] == "C"].iloc[0]["T"] == 1
