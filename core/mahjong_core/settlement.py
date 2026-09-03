"""Turning balances into who-pays-whom instructions.

Mirrors taidi_core.settlement's two strategies. `minimize_transfers` is
re-exported as-is from taidi_core — it only operates on a plain balances
dict, no Transfer type involved, so there's nothing Mahjong-specific to
reimplement. `pairwise_net` is reimplemented here against mahjong_core's own
Transfer type (see ADR-0006 on why the types aren't shared: TransferKind's
values differ per game).
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from taidi_core.models import Settlement
from taidi_core.settlement import minimize_transfers as minimize_transfers

from .models import Transfer

__all__ = ["pairwise_net", "minimize_transfers"]


def pairwise_net(transfers: list[Transfer]) -> list[Settlement]:
    net: dict[frozenset[UUID], int] = defaultdict(int)
    canonical: dict[frozenset[UUID], tuple[UUID, UUID]] = {}
    for t in transfers:
        key = frozenset((t.from_player, t.to_player))
        a, b = canonical.setdefault(key, (t.from_player, t.to_player))
        signed = t.amount_cents if t.from_player == a else -t.amount_cents
        net[key] += signed

    settlements = []
    for key, amount in net.items():
        if amount == 0:
            continue
        a, b = canonical[key]
        if amount > 0:
            settlements.append(Settlement(from_player=a, to_player=b, amount_cents=amount))
        else:
            settlements.append(Settlement(from_player=b, to_player=a, amount_cents=-amount))
    return settlements
