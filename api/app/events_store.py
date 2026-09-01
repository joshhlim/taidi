"""Persistence for rooms and their event logs, and the fold that turns them
back into a taidi_core RoomState."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from taidi_core import machine
from taidi_core.models import Event, EventType, RoomState

from .db import events as events_table
from .db import rooms as rooms_table

_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I — easy to read aloud


def generate_invite_code(length: int = 6) -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(length))


class RoomNotFound(Exception):
    pass


async def create_room(
    session: AsyncSession, *, room_id: UUID, host_id: UUID, host_display_name: str, now: datetime
) -> tuple[RoomState, str]:
    invite_code = generate_invite_code()
    await session.execute(
        insert(rooms_table).values(
            room_id=room_id,
            invite_code=invite_code,
            host_id=host_id,
            host_display_name=host_display_name,
            created_at=now,
        )
    )
    await session.commit()
    state = RoomState.new(
        room_id=room_id, host_id=host_id, host_display_name=host_display_name, now=now
    )
    return state, invite_code


async def resolve_invite_code(session: AsyncSession, invite_code: str) -> UUID | None:
    row = (
        await session.execute(
            select(rooms_table.c.room_id).where(rooms_table.c.invite_code == invite_code.upper())
        )
    ).first()
    return row.room_id if row else None


async def _load_room_seed(session: AsyncSession, room_id: UUID) -> Any:
    row = (
        await session.execute(select(rooms_table).where(rooms_table.c.room_id == room_id))
    ).first()
    if row is None:
        raise RoomNotFound(room_id)
    return row


async def load_events(session: AsyncSession, room_id: UUID) -> list[Event]:
    rows = await session.execute(
        select(events_table).where(events_table.c.room_id == room_id).order_by(events_table.c.seq)
    )
    return [
        Event(
            event_id=r.id,
            room_id=r.room_id,
            seq=r.seq,
            type=EventType(r.type),
            actor=r.actor,
            payload=r.payload,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def rebuild_state(session: AsyncSession, room_id: UUID) -> RoomState:
    seed = await _load_room_seed(session, room_id)
    state = RoomState.new(
        room_id=seed.room_id,
        host_id=seed.host_id,
        host_display_name=seed.host_display_name,
        now=seed.created_at,
    )
    return machine.fold(state, await load_events(session, room_id))


async def append_events(session: AsyncSession, room_id: UUID, new_events: list[Event]) -> None:
    """Insert new events. Raises IntegrityError (unmapped) on a (room_id, seq)
    collision — the caller maps that to a 409 for the loser of a race."""
    if not new_events:
        return
    await session.execute(
        insert(events_table),
        [
            {
                "id": e.event_id,
                "room_id": room_id,
                "seq": e.seq,
                "type": e.type.value,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in new_events
        ],
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
