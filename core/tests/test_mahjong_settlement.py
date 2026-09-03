"""mahjong_core.settlement.pairwise_net against mahjong_core's own Transfer type.

minimize_transfers isn't retested here — mahjong_core re-exports it as-is
from taidi_core.settlement (it only operates on a plain balances dict, no
Transfer type involved), and it's already covered by taidi_core's own
test_settlement.py.
"""

from __future__ import annotations

from uuid import uuid4

from mahjong_core.models import Transfer, TransferKind
from mahjong_core.settlement import pairwise_net


def _t(frm, to, amount, kind=TransferKind.YAO, hand_no=1):
    return Transfer(from_player=frm, to_player=to, amount_cents=amount, kind=kind, hand_no=hand_no)


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
    transfers = [_t(A, B, 500), _t(C, B, 300)]
    settlements = pairwise_net(transfers)
    pairs = {frozenset((s.from_player, s.to_player)) for s in settlements}
    assert frozenset((A, C)) not in pairs
    assert len(settlements) == 2
