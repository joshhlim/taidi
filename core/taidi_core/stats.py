"""Lifetime player statistics, derived from a list of ended rooms."""

from __future__ import annotations

from uuid import UUID

from .models import PlayerStats, RoomState, RoomStatus


def player_lifetime_stats(rooms: list[RoomState]) -> dict[UUID, PlayerStats]:
    """Lifetime stats per player across every ENDED room. Non-ended rooms are ignored."""
    stats: dict[UUID, PlayerStats] = {}
    for room in rooms:
        if room.status != RoomStatus.ENDED:
            continue
        for pid, balance in room.balances.items():
            member = room.members.get(pid)
            name = member.display_name if member else str(pid)
            s = stats.get(pid)
            if s is None:
                s = PlayerStats(player_id=pid, display_name=name)
                stats[pid] = s
            s.display_name = name
            s.games += 1
            s.total_cents += balance
            if balance > 0:
                s.wins += 1
            elif balance < 0:
                s.losses += 1
            else:
                s.ties += 1
            if room.ended_at and (s.last_played is None or room.ended_at > s.last_played):
                s.last_played = room.ended_at
    return stats
