"""The scoring engine: pure functions from card counts to money transfers.

Split in two, because in the live room product a special hand is settled
immediately when claimed, independently of when (or whether) the round it
happened in gets resolved:

- `compute_card_transfers` — the winner-vs-losers settlement once every
  loser's card count is in. Port of the original Streamlit `compute_payouts`.
- `compute_special_transfer` — one special-hand claim, settled on the spot.

Bump ENGINE_VERSION whenever the scoring math changes; it's stamped onto
every resolved round so old rounds can always be told apart from new logic.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .models import GameRules, Transfer, TransferKind

ENGINE_VERSION = "1"


def compute_card_transfers(
    card_counts: dict[UUID, int], rules: GameRules, round_no: int
) -> tuple[list[Transfer], UUID]:
    """
    Compute the winner/loser transfers for one round from final card counts.

    1) Winner = the player with 0 cards.
    2) Every loser pays the winner: cards_left x multiplier x card_value.
    3) If difference_payouts is on, each loser also pays every less-losing
       loser the difference in card counts x their own multiplier.
    4) Every loser additionally pays the winner base_cards worth, unmultiplied.

    Special hands are NOT included here — see compute_special_transfer.
    """
    winners = [p for p, c in card_counts.items() if c == 0]
    if len(winners) != 1:
        raise ValueError("Exactly one player must end the round with 0 cards.")
    winner = winners[0]

    remaining = sorted(
        ((p, c) for p, c in card_counts.items() if p != winner),
        key=lambda x: x[1],
    )

    transfers: list[Transfer] = []
    for i, (payer, payer_cards) in enumerate(remaining):
        if payer_cards <= 0:
            continue
        m = rules.multiplier(payer_cards)
        transfers.append(
            Transfer(
                from_player=payer,
                to_player=winner,
                cards=payer_cards,
                mult=m,
                amount_cents=payer_cards * m * rules.card_value_cents,
                kind=TransferKind.CARDS,
                round_no=round_no,
            )
        )
        if rules.difference_payouts:
            for j in range(i):
                receiver, receiver_cards = remaining[j]
                diff = payer_cards - receiver_cards
                if diff > 0:
                    transfers.append(
                        Transfer(
                            from_player=payer,
                            to_player=receiver,
                            cards=diff,
                            mult=m,
                            amount_cents=diff * m * rules.card_value_cents,
                            kind=TransferKind.DIFFERENCE,
                            round_no=round_no,
                        )
                    )

    if rules.base_cards > 0:
        for payer, _ in remaining:
            transfers.append(
                Transfer(
                    from_player=payer,
                    to_player=winner,
                    cards=rules.base_cards,
                    mult=1,
                    amount_cents=rules.base_cards * rules.card_value_cents,
                    kind=TransferKind.BASE,
                    round_no=round_no,
                )
            )

    return transfers, winner


def compute_special_transfer(
    claimer: UUID, other_members: list[UUID], rules: GameRules, round_no: int
) -> list[Transfer]:
    """One special-hand claim: every other member pays the claimer immediately."""
    amount = rules.special_hand_cards * rules.card_value_cents
    return [
        Transfer(
            from_player=member,
            to_player=claimer,
            cards=rules.special_hand_cards,
            mult=1,
            amount_cents=amount,
            kind=TransferKind.SPECIAL,
            round_no=round_no,
        )
        for member in other_members
    ]


class ScoringRule(Protocol):
    """One card game's scoring logic. Taidi is the only implementation today."""

    def compute_card_transfers(
        self, card_counts: dict[UUID, int], rules: GameRules, round_no: int
    ) -> tuple[list[Transfer], UUID]: ...


class TaidiScoringRule:
    """Default ScoringRule implementation for Taidi (Big Two)."""

    def compute_card_transfers(
        self, card_counts: dict[UUID, int], rules: GameRules, round_no: int
    ) -> tuple[list[Transfer], UUID]:
        return compute_card_transfers(card_counts, rules, round_no)
