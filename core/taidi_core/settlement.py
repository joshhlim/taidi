"""Turning balances into who-pays-whom instructions.

Two strategies, both pure:

- `pairwise_net` nets all the money that actually moved between each pair of
  players during the game down to one transfer per pair. You only ever pay
  someone you actually exchanged money with.
- `minimize_transfers` ignores history and greedily matches the biggest
  creditor with the biggest debtor from final balances alone — fewer
  transactions, but you can end up paying someone you never lost to.

Default in the product is pairwise netting; minimize_transfers is opt-in.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from .models import Settlement, Transfer


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


def minimize_transfers(balances: dict[UUID, int]) -> list[Settlement]:
    remaining: dict[UUID, int] = dict(balances)
    creditor_ids = sorted(
        (pid for pid, amt in balances.items() if amt > 0), key=lambda pid: -balances[pid]
    )
    debtor_ids = sorted(
        (pid for pid, amt in balances.items() if amt < 0), key=lambda pid: balances[pid]
    )

    settlements: list[Settlement] = []
    ci = di = 0
    while ci < len(creditor_ids) and di < len(debtor_ids):
        cid, did = creditor_ids[ci], debtor_ids[di]
        amount = min(remaining[cid], -remaining[did])
        if amount > 0:
            settlements.append(Settlement(from_player=did, to_player=cid, amount_cents=amount))
        remaining[cid] -= amount
        remaining[did] += amount
        if remaining[cid] == 0:
            ci += 1
        if remaining[did] == 0:
            di += 1
    return settlements
