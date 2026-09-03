"""The room endpoints — the only write path to taidi_core rooms.

Every mutating endpoint follows the same shape: rebuild the current
RoomState from the event log, hand the command to the matching
taidi_core.machine function (which validates and returns event(s) without
mutating anything), persist those events, and return the freshly rebuilt
state. MachineError subclasses map directly to HTTP status codes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from taidi_core import machine
from taidi_core.errors import IllegalTransition, NotAuthorized, SeqConflict
from taidi_core.models import Event, RoomState

from ..auth import CurrentUser, get_current_user
from ..db import get_session
from ..events_store import (
    RoomNotFound,
    append_events,
    create_room,
    rebuild_state_with_invite,
    resolve_invite_code,
)
from ..schemas import (
    CreateRoomRequest,
    SeqOnlyRequest,
    StartGameRequest,
    SubmitCardsRequest,
    SubmitForRequest,
)
from ..time import utcnow

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _get_state_with_invite_or_404(
    session: AsyncSession, room_id: UUID
) -> tuple[RoomState, str]:
    try:
        return await rebuild_state_with_invite(session, room_id)
    except RoomNotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found.") from e


def _as_json(state: RoomState, invite_code: str) -> dict[str, Any]:
    return {**state.model_dump(mode="json"), "invite_code": invite_code}


async def _dispatch(
    session: AsyncSession,
    room_id: UUID,
    build_events: Callable[[RoomState], list[Event]],
) -> dict[str, Any]:
    """Rebuild state, run one command against it, persist, and return the new state.

    Retries once on a genuine DB-level race (two requests computing the same
    next seq); the second attempt rebuilds fresh state and re-validates, so
    it either succeeds against the now-current state or raises a proper
    MachineError instead of a raw integrity error.
    """
    for _attempt in range(2):
        state, invite_code = await _get_state_with_invite_or_404(session, room_id)
        try:
            new_events = build_events(state)
        except SeqConflict as e:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {"message": str(e), "state": _as_json(state, invite_code)},
            ) from e
        except NotAuthorized as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e
        except IllegalTransition as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

        try:
            await append_events(session, room_id, new_events)
        except IntegrityError:
            continue  # someone else's event landed first — rebuild and retry once

        new_state = machine.fold(state, new_events)
        return _as_json(new_state, invite_code)

    raise HTTPException(status.HTTP_409_CONFLICT, "Too many concurrent updates — please retry.")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    _body: CreateRoomRequest = CreateRoomRequest(),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    room_id = uuid4()
    state, invite_code = await create_room(
        session,
        room_id=room_id,
        host_id=user.user_id,
        host_display_name=user.display_name,
        now=utcnow(),
    )
    return _as_json(state, invite_code)


@router.get("/by-code/{invite_code}")
async def by_code(invite_code: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    room_id = await resolve_invite_code(session, invite_code)
    if room_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No room with that code.")
    return {"room_id": str(room_id)}


@router.get("/{room_id}/state")
async def get_state(
    room_id: UUID,
    _user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    state, invite_code = await _get_state_with_invite_or_404(session, room_id)
    return _as_json(state, invite_code)


@router.post("/{room_id}/join")
async def join(
    room_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.join_player(
            state,
            expected_seq=state.seq,
            player_id=user.user_id,
            display_name=user.display_name,
            now=utcnow(),
        ),
    )


@router.post("/{room_id}/leave")
async def leave(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.leave_room(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )


@router.post("/{room_id}/disband")
async def disband(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.disband_room(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )


@router.post("/{room_id}/start")
async def start(
    room_id: UUID,
    body: StartGameRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.start_game(
            state,
            expected_seq=body.expected_seq,
            actor=user.user_id,
            rules=body.rules,
            now=utcnow(),
        ),
    )


@router.post("/{room_id}/win")
async def win(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.claim_win(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )


@router.post("/{room_id}/cards")
async def submit_cards(
    room_id: UUID,
    body: SubmitCardsRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.submit_cards(
            state,
            expected_seq=body.expected_seq,
            actor=user.user_id,
            cards=body.cards,
            now=utcnow(),
        ),
    )


@router.post("/{room_id}/submit-for")
async def submit_for(
    room_id: UUID,
    body: SubmitForRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.submit_for(
            state,
            expected_seq=body.expected_seq,
            actor=user.user_id,
            target_player=body.target_player,
            cards=body.cards,
            now=utcnow(),
        ),
    )


@router.post("/{room_id}/special")
async def special_hand(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.add_special_hand(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )


@router.post("/{room_id}/void")
async def void(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.void_last_round(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )


@router.post("/{room_id}/end")
async def end(
    room_id: UUID,
    body: SeqOnlyRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _dispatch(
        session,
        room_id,
        lambda state: machine.end_game(
            state, expected_seq=body.expected_seq, actor=user.user_id, now=utcnow()
        ),
    )
