# ADR-0006: Mahjong as a parallel `mahjong_core` package, not a `taidi_core` refactor

- Status: accepted
- Date: 2026-09-03

## Context

Adding a second playable game (Mahjong) is the first real use of the
"second game type" idea sketched in the original roadmap. Auditing the
current stack found there is no `game_type` concept anywhere — not in the
DB, the API schemas, `RoomState`, or the frontend types. Everything —
`EventType`, `apply()`/`fold()`, `GameRules`, `RoundState` — is Taidi-specific
and hardcoded. The `ScoringRule` Protocol in `core/taidi_core/rules.py` looks
like an extension point but is dead code: `machine.py` calls the free
function directly, never through it.

Mahjong's actual shape is very different from Taidi's round-based
card-count model: it has no "everyone submits a count" collecting phase at
all. Instead it's a continuous stream of independent actions (YAO, GANG, HU)
against an ongoing hand, plus dealer/wind bookkeeping that Taidi has no
equivalent of.

## Decision

Build Mahjong as a new sibling package, `core/mahjong_core/`, with its own
`EventType`, state model, and `machine.py` — mirroring `taidi_core`'s shape
exactly but sharing nothing at the type level. Rewriting `taidi_core.apply()`'s
closed `EventType` switch into a generic per-game dispatcher was considered
and rejected: it would touch every line of a well-tested, currently correct
engine for no player-facing benefit, purely to accommodate a game whose
event shape barely overlaps Taidi's anyway.

What's reused as-is, because it's already genuinely game-agnostic:

- `events_store.py`/`db.py`'s event-sourcing and optimistic-concurrency
  machinery. The `rooms`/`events` tables are just `room_id, seq, type: str,
  payload: jsonb` — both engines' event type strings coexist in the same
  tables without conflict.
- `taidi_core.settlement`'s `Transfer`/balance/netting utilities — no
  Taidi-only fields.
- `taidi_core.stats.player_lifetime_stats` — only reads `.balances`/
  `.members`, so `MahjongRoomState` gets lifetime stats for free by exposing
  the same attribute names.

What's new:

- `rooms.game_type` column (`taidi` | `mahjong`, default `taidi`) so the API
  knows which core package's `machine` module to fold a room's events
  through.
- A parallel `api/app/routers/mahjong.py`, using the same `_dispatch()`-and-
  command-function pattern already established in `routers/rooms.py`.
- Frontend `RoomState.game_type` discriminator; `room/[roomId]/page.tsx`
  branches at the top into `<TaidiRoom>` (existing code, extracted as-is) or
  `<MahjongRoom>`.

## Consequences

- Taidi's engine is completely untouched by this work — zero regression risk
  to the tested, currently-deployed game.
- Some duplication is accepted: leave/disband-room logic, the `_dispatch`
  pattern's shape, and general command/apply structure are hand-mirrored
  between the two core packages rather than shared through a common base.
  This is consistent with the existing precedent (`ScoringRule` was already
  an unused abstraction) — a real shared abstraction can be extracted later
  if and when a third game type shows the actual common shape, not
  speculatively now for a game count of two.
- Adding a third game type follows the same pattern: a new `*_core` package,
  a new `game_type` enum value, a new parallel router, a new frontend
  branch. No part of this decision needs revisiting to do that again.
