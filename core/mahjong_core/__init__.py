"""mahjong_core: the pure-Python domain core for Mahjong rooms.

Mirrors taidi_core's shape (see ADR-0006) but is a separate package with its
own event-sourced state machine — no shared state-machine code, though
genuinely game-agnostic pieces (Member, Settlement, PlayerStats, RoomStatus,
the MachineError hierarchy, minimize_transfers) are imported from
taidi_core rather than duplicated.
"""

from taidi_core.errors import IllegalTransition, MachineError, NotAuthorized, SeqConflict
from taidi_core.models import Member, PlayerStats, RoomStatus, Settlement

from . import machine, settlement, stats
from .models import Event, EventType, HandState, MahjongRules, RoomState, Transfer, TransferKind
from .rules import (
    ENGINE_VERSION,
    gang_amount_angang,
    gang_amount_other,
    gang_amount_self,
    hu_amount_bao,
    hu_amount_direct,
    hu_amount_zimo_each,
    yao_amount,
)

__all__ = [
    "machine",
    "settlement",
    "stats",
    "MachineError",
    "IllegalTransition",
    "NotAuthorized",
    "SeqConflict",
    "Event",
    "EventType",
    "HandState",
    "MahjongRules",
    "Member",
    "PlayerStats",
    "RoomState",
    "RoomStatus",
    "Settlement",
    "Transfer",
    "TransferKind",
    "ENGINE_VERSION",
    "gang_amount_angang",
    "gang_amount_other",
    "gang_amount_self",
    "hu_amount_bao",
    "hu_amount_direct",
    "hu_amount_zimo_each",
    "yao_amount",
]
