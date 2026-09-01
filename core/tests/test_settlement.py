"""Settlement: pairwise netting and greedy debt minimization."""

from __future__ import annotations

from uuid import uuid4

from taidi_core.models import Transfer, TransferKind
from taidi_core.settlement import minimize_transfers, pairwise_net


def _t(frm, to, amount, kind=TransferKind.CARDS, round_no=1):
    return Transfer(
        from_player=frm, to_player=to, cards=1, amount_cents=amount, kind=kind, round_no=round_no
    )


def test_pairwise_net_collapses_back_and_forth_transfers():
    A, B = uuid4(), uuid4()
    transfers = [_t(A, B, 500), _t(B, A, 200), _t(A, B, 100)]
    settlements = pairwise_net(transfers)
    assert len(settlements) == 1
    s = settlements[0]
    assert s.from_player == A and s.to_player == B and s.amount_cents == 400


def test_pairwise_net_skips_pairs_that_cancel_out():
    A, B = uuid4(), uuid4()
    transfers = [_t(A, B, 300), _t(B, A, 300)]
    assert pairwise_net(transfers) == []


def test_pairwise_net_never_creates_a_transfer_between_players_who_never_transacted():
    A, B, C = uuid4(), uuid4(), uuid4()
    # A and C never directly exchanged money
    transfers = [_t(A, B, 500), _t(C, B, 300)]
    settlements = pairwise_net(transfers)
    pairs = {frozenset((s.from_player, s.to_player)) for s in settlements}
    assert frozenset((A, C)) not in pairs
    assert len(settlements) == 2


def test_minimize_transfers_settles_final_balances_to_zero():
    A, B, C = uuid4(), uuid4(), uuid4()
    balances = {A: 700, B: -300, C: -400}
    settlements = minimize_transfers(balances)
    net = dict.fromkeys(balances, 0)
    for s in settlements:
        net[s.from_player] -= s.amount_cents
        net[s.to_player] += s.amount_cents
    for pid, bal in balances.items():
        assert net[pid] == bal


def test_minimize_transfers_uses_fewer_or_equal_transactions_than_pairwise():
    # 4-cycle-ish debts where pairwise would need more legs than greedy netting from balances.
    A, B, C, D = uuid4(), uuid4(), uuid4(), uuid4()
    transfers = [_t(A, B, 100), _t(B, C, 100), _t(C, D, 100)]
    balances = {A: -100, B: 0, C: 0, D: 100}
    assert len(minimize_transfers(balances)) <= len(pairwise_net(transfers))
