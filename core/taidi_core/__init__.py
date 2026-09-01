"""taidi_core: the pure-Python domain core shared by every Taidi frontend.

No I/O, no framework dependencies beyond pydantic. `machine` is the
event-sourced room/round state machine; `rules` is the scoring engine;
`stats` and `settlement` derive reporting and payout instructions from
ended rooms.
"""

from . import machine, settlement, stats
from .errors import IllegalTransition, MachineError, NotAuthorized, SeqConflict
from .models import (
    Event,
    EventType,
    GameRules,
    Member,
    PlayerStats,
    RoomState,
    RoomStatus,
    RoundPhase,
    RoundState,
    Settlement,
    Transfer,
    TransferKind,
)
from .rules import (
    ENGINE_VERSION,
    ScoringRule,
    TaidiScoringRule,
    compute_card_transfers,
    compute_special_transfer,
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
    "GameRules",
    "Member",
    "PlayerStats",
    "RoomState",
    "RoomStatus",
    "RoundPhase",
    "RoundState",
    "Settlement",
    "Transfer",
    "TransferKind",
    "ENGINE_VERSION",
    "ScoringRule",
    "TaidiScoringRule",
    "compute_card_transfers",
    "compute_special_transfer",
]
