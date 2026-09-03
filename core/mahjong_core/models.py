"""Typed vocabulary for mahjong_core: rules, hands, transfers, rooms, events.

Mirrors taidi_core/models.py's conventions (integer cents, frozen rule
models, event-sourced RoomState) but for Mahjong's very different shape:
no round-based card-count collection — a continuous stream of YAO/GANG/HU
declarations against an always-open hand, plus dealer/wind bookkeeping
Taidi has no equivalent of. See ADR-0006 for why this is a separate
package rather than a taidi_core extension.

Genuinely game-agnostic types (Member, Settlement, PlayerStats, RoomStatus,
the MachineError hierarchy) are imported from taidi_core rather than
duplicated here — see __init__.py.

Seats are plain ints 0-3, defaulting to join order; the host can rearrange
them via machine.assign_seats before starting. The 東南西北 nicknames are a
frontend display concern only — the backend never needs to know them.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from taidi_core.models import Member, RoomStatus


class MahjongRules(BaseModel):
    """Everything about how a game is scored. All of it configurable."""

    model_config = ConfigDict(frozen=True)

    yao_unit_cents: int = 100
    gang_unit_cents: int = 100
    tai_unit_cents: int = 100
    zimo_unit_cents: int = 100
    max_tai: int = 10

    @model_validator(mode="after")
    def _validate(self) -> MahjongRules:
        if (
            min(
                self.yao_unit_cents, self.gang_unit_cents, self.tai_unit_cents, self.zimo_unit_cents
            )
            < 0
        ):
            raise ValueError("Rule values can't be negative.")
        if self.max_tai < 1:
            raise ValueError("max_tai must be at least 1.")
        return self

    def describe(self) -> str:
        return (
            f"yao ${self.yao_unit_cents / 100:.2f} · gang ${self.gang_unit_cents / 100:.2f} · "
            f"${self.tai_unit_cents / 100:.2f}/tai (zimo ${self.zimo_unit_cents / 100:.2f}/tai) · "
            f"max {self.max_tai} tai"
        )


class TransferKind(StrEnum):
    YAO = "yao"
    GANG = "gang"
    HU = "hu"
    BAO = "bao"


class Transfer(BaseModel):
    """One payment from one player to another."""

    model_config = ConfigDict(frozen=True)

    from_player: UUID
    to_player: UUID
    amount_cents: int
    kind: TransferKind
    hand_no: int


class HandState(BaseModel):
    hand_no: int
    wind: int
    dealer_seat: int
    had_gang: bool = False
    closed: bool = False
    winner: UUID | None = None
    transfers: list[Transfer] = Field(default_factory=list)


class RoomState(BaseModel):
    """The full, derivable state of one room. Rebuilt by folding events through machine.apply()."""

    room_id: UUID
    status: RoomStatus = RoomStatus.LOBBY
    seq: int = 0
    host_id: UUID
    members: dict[UUID, Member] = Field(default_factory=dict)
    rules: MahjongRules | None = None
    hands: list[HandState] = Field(default_factory=list)
    balances: dict[UUID, int] = Field(default_factory=dict)
    created_at: datetime
    ended_at: datetime | None = None
    # Set once the 4-winds cycle completes (last seat of the last wind closes
    # on a win) — only the host's continue_wind or end_game can proceed.
    pending_wind_decision: bool = False

    @classmethod
    def new(
        cls, *, room_id: UUID, host_id: UUID, host_display_name: str, now: datetime
    ) -> RoomState:
        host = Member(player_id=host_id, display_name=host_display_name, seat=0)
        return cls(
            room_id=room_id,
            host_id=host_id,
            members={host_id: host},
            balances={host_id: 0},
            created_at=now,
        )

    @property
    def current_hand(self) -> HandState | None:
        return self.hands[-1] if self.hands else None

    @property
    def member_ids_by_seat(self) -> list[UUID]:
        """Member ids ordered by seat. Only meaningful once exactly 4 have joined."""
        return sorted(self.members, key=lambda pid: self.members[pid].seat)


class EventType(StrEnum):
    PLAYER_JOINED = "player_joined"
    SEATS_ASSIGNED = "seats_assigned"
    GAME_STARTED = "game_started"
    YAO_DECLARED = "yao_declared"
    GANG_DECLARED = "gang_declared"
    HU_DECLARED = "hu_declared"
    NO_WIN_DECLARED = "no_win_declared"
    WIND_CONTINUED = "wind_continued"
    GAME_ENDED = "game_ended"
    PLAYER_LEFT = "player_left"
    ROOM_DISBANDED = "room_disbanded"


class Event(BaseModel):
    """One entry in a room's append-only log. `payload` mirrors the `events.payload jsonb` column."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    room_id: UUID
    seq: int
    type: EventType
    actor: UUID | None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
