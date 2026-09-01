"""Game rules and scoring logic for Taidi Tracker."""

from dataclasses import asdict, dataclass, fields

import pandas as pd


@dataclass
class GameRules:
    """Everything about how a game is scored. All of it configurable."""

    card_value: float = 0.20  # $ per card
    base_cards: int = 2  # flat cards' worth each loser pays the winner (no multiplier)
    multipliers_enabled: bool = True  # double/triple penalty for being caught with many cards
    double_threshold: int = 10  # payer cards >= this -> x2
    triple_threshold: int = 13  # payer cards >= this -> x3
    difference_payouts: bool = True  # losers also settle card-count differences among themselves
    special_hands_enabled: bool = True
    special_hand_cards: int = 5  # cards' worth each special hand collects from every other player

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "GameRules":
        if not d:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def multiplier(self, payer_cards: int) -> int:
        if not self.multipliers_enabled:
            return 1
        if payer_cards >= self.triple_threshold:
            return 3
        if payer_cards >= self.double_threshold:
            return 2
        return 1

    def describe(self) -> str:
        """Short human-readable summary, shown in the history log."""
        parts = [f"${self.card_value:.2f}/card"]
        if self.base_cards:
            parts.append(f"base {self.base_cards}")
        if self.multipliers_enabled:
            parts.append(f"x2 at {self.double_threshold}+, x3 at {self.triple_threshold}+")
        else:
            parts.append("no multipliers")
        parts.append("difference payouts" if self.difference_payouts else "winner-only")
        if self.special_hands_enabled:
            parts.append(f"special +{self.special_hand_cards}")
        return " · ".join(parts)


def compute_payouts(card_counts: dict, rules: GameRules):
    """
    Compute all transfers for a round from final card counts.

    1) Winner = the player with 0 cards.
    2) Every loser pays the winner: cards_left x multiplier x card_value.
    3) If difference_payouts is on, each loser also pays every less-losing
       loser the difference in card counts x their own multiplier.
    4) Every loser additionally pays the winner base_cards worth, unmultiplied.

    Returns (transfers, winner) where transfers is a list of dicts:
    {"from", "to", "cards", "mult", "amount", "kind"}.
    """
    winners = [p for p, c in card_counts.items() if c == 0]
    if len(winners) != 1:
        raise ValueError("Exactly one player must end the round with 0 cards.")
    winner = winners[0]

    remaining = sorted(
        ((p, c) for p, c in card_counts.items() if p != winner),
        key=lambda x: x[1],
    )

    transfers = []
    for i, (payer, payer_cards) in enumerate(remaining):
        if payer_cards <= 0:
            continue
        m = rules.multiplier(payer_cards)
        transfers.append(
            {
                "from": payer,
                "to": winner,
                "cards": payer_cards,
                "mult": m,
                "amount": payer_cards * m * rules.card_value,
                "kind": "cards",
            }
        )
        if rules.difference_payouts:
            for j in range(i):
                receiver, receiver_cards = remaining[j]
                diff = payer_cards - receiver_cards
                if diff > 0:
                    transfers.append(
                        {
                            "from": payer,
                            "to": receiver,
                            "cards": diff,
                            "mult": m,
                            "amount": diff * m * rules.card_value,
                            "kind": "difference",
                        }
                    )

    if rules.base_cards > 0:
        for payer, _ in remaining:
            transfers.append(
                {
                    "from": payer,
                    "to": winner,
                    "cards": rules.base_cards,
                    "mult": 1,
                    "amount": rules.base_cards * rules.card_value,
                    "kind": "base",
                }
            )

    return transfers, winner


class CardGameTracker:
    def __init__(self, players, rules: GameRules):
        self.players = list(players)
        self.rules = rules
        self.balances = {p: 0.0 for p in self.players}
        self.history = pd.DataFrame(index=self.players)
        self.tx_log: list[dict] = []  # one record per round: {"round", "winner", "transfers"}

    def play_round(self, card_counts_list, round_name=None, special_hand_counts=None) -> dict:
        if len(card_counts_list) != len(self.players):
            raise ValueError(
                f"Expected {len(self.players)} card counts, got {len(card_counts_list)}"
            )

        card_counts = dict(zip(self.players, card_counts_list, strict=True))
        round_name = round_name or f"Round {self.history.shape[1] + 1}"

        transfers, winner = compute_payouts(card_counts, self.rules)

        if self.rules.special_hands_enabled and special_hand_counts:
            for special_player, count in special_hand_counts.items():
                if special_player in self.players and count > 0:
                    cards = self.rules.special_hand_cards * count
                    for player in self.players:
                        if player != special_player:
                            transfers.append(
                                {
                                    "from": player,
                                    "to": special_player,
                                    "cards": cards,
                                    "mult": 1,
                                    "amount": cards * self.rules.card_value,
                                    "kind": "special",
                                }
                            )

        for t in transfers:
            self.balances[t["from"]] -= t["amount"]
            self.balances[t["to"]] += t["amount"]

        self.history[round_name] = pd.Series(self.balances)
        record = {"round": round_name, "winner": winner, "transfers": transfers}
        self.tx_log.append(record)
        return record

    @property
    def rounds_played(self) -> int:
        return self.history.shape[1]

    def get_summary(self) -> pd.DataFrame:
        summary = self.history.copy()
        summary["Total"] = pd.Series(self.balances)
        return summary

    # ---- persistence ----
    def to_snapshot(self) -> dict:
        return {
            "players": self.players,
            "rules": self.rules.to_dict(),
            "balances": self.balances,
            "history": self.history.to_dict(orient="split"),
            "tx_log": self.tx_log,
        }

    @classmethod
    def from_snapshot(cls, snap: dict) -> "CardGameTracker":
        tracker = cls(snap["players"], GameRules.from_dict(snap.get("rules")))
        tracker.balances = {p: float(v) for p, v in snap["balances"].items()}
        hist = snap["history"]
        tracker.history = pd.DataFrame(
            data=hist["data"], index=hist["index"], columns=hist["columns"]
        )
        tracker.tx_log = snap.get("tx_log", [])
        return tracker


# ============== Lifetime stats (always derived from the archive) ==============


def player_stats_df(archive: list[dict]) -> pd.DataFrame:
    """Lifetime stats per player, computed fresh from archived games."""
    stats: dict[str, dict] = {}
    for entry in archive:
        for name, net in entry.get("final_totals", {}).items():
            s = stats.setdefault(
                name, {"games": 0, "total": 0.0, "wins": 0, "losses": 0, "ties": 0, "last": ""}
            )
            s["games"] += 1
            s["total"] += float(net)
            if net > 0:
                s["wins"] += 1
            elif net < 0:
                s["losses"] += 1
            else:
                s["ties"] += 1
            s["last"] = max(s["last"], entry.get("created_at", ""))

    if not stats:
        return pd.DataFrame(
            columns=["Player", "Games", "Total", "Avg/Game", "W", "L", "T", "Last Played"]
        )

    rows = [
        {
            "Player": name,
            "Games": s["games"],
            "Total": s["total"],
            "Avg/Game": s["total"] / s["games"],
            "W": s["wins"],
            "L": s["losses"],
            "T": s["ties"],
            "Last Played": s["last"] or "-",
        }
        for name, s in stats.items()
    ]
    return (
        pd.DataFrame(rows)
        .sort_values(["Total", "Games"], ascending=[False, False])
        .reset_index(drop=True)
    )


def player_history_df(archive: list[dict], player_name: str) -> pd.DataFrame:
    """Per-game results for one player, from archived games."""
    rows = []
    for entry in archive:
        totals = entry.get("final_totals", {})
        if player_name in totals:
            rules = GameRules.from_dict(entry.get("rules"))
            rows.append(
                {
                    "When": entry.get("created_at", ""),
                    "Rounds": entry.get("rounds_played", 0),
                    "Card Value": rules.card_value,
                    "Net": float(totals[player_name]),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["When", "Rounds", "Card Value", "Net"])
    return pd.DataFrame(rows).sort_values("When", ascending=False).reset_index(drop=True)
