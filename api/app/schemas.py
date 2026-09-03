"""Request bodies for the room command endpoints.

Every mutating command carries expected_seq (optimistic concurrency — see
taidi_core.machine and ADR-0001). Responses are always the full RoomState as
JSON (RoomState.model_dump(mode="json")), so the client never needs a second
round-trip to know what happened.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from taidi_core.models import GameRules


class CreateRoomRequest(BaseModel):
    game_type: Literal["taidi", "mahjong"] = "taidi"


class StartGameRequest(BaseModel):
    expected_seq: int
    rules: GameRules = GameRules()


class SeqOnlyRequest(BaseModel):
    expected_seq: int


class SubmitCardsRequest(BaseModel):
    expected_seq: int
    cards: int


class SubmitForRequest(BaseModel):
    expected_seq: int
    target_player: UUID
    cards: int
