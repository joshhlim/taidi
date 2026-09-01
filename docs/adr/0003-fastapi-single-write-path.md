# ADR-0003: FastAPI as the single write path; pluggable dev/Supabase auth

- Status: accepted
- Date: 2026-09-01

## Context

ADR-0001 required a stateless API as the only write path to a room's event
log, with clients reading via a managed realtime layer (Supabase Realtime)
instead. Building that API surfaced two decisions worth recording.

## Decision

1. **The API persists nothing but the event log itself.** The `rooms` table
   holds only what a room needs to exist before any event is possible — its
   invite code and the seed `RoomState.new()` is built from (host, created
   at). Every other field is derived by folding `events` through
   `taidi_core.machine.fold` on every read. Given a Taidi game is tens of
   rounds, replay-per-request is cheap and keeps there from ever being a
   second source of truth to drift out of sync with the log.
2. **Auth is a pluggable JWT verifier with two modes, both producing the
   same `CurrentUser(user_id, display_name)`.** In `dev` mode (the default),
   `POST /auth/dev-login` mints an HS256 token for any display name — no
   external identity provider needed for local development, tests, or CI.
   In `supabase` mode, the same verification path checks tokens against the
   Supabase project's JWT secret instead. Nothing downstream of
   `get_current_user` knows or cares which mode produced the token. This
   means the whole vertical slice — schema, concurrency, the state machine,
   the frontend — can be built and proven end to end before a Supabase
   project exists, and switching modes at deploy time is a config change,
   not a code change.
3. **Optimistic concurrency has two layers.** Every command's `expected_seq`
   is checked in Python against the just-rebuilt state first (the common
   case: a client with any stale data). A genuine race between two requests
   that both rebuilt the same state and both computed the same next `seq` is
   caught by the database's `UNIQUE(room_id, seq)` constraint — the losing
   `INSERT` raises `IntegrityError`, and the endpoint rebuilds and retries
   once rather than surfacing a raw DB error.
4. **Migrations are Alembic, targeting `TAIDI_DATABASE_URL` directly** (not a
   separate URL in `alembic.ini`) — dev, test, and CI all migrate the same
   database the app itself would connect to, so "migrations pass" and "the
   app can start" are never two different claims.

## Consequences

- A local `docker compose up -d postgres` plus `alembic upgrade head` is the
  entire local setup — no cloud account required to develop or test the API.
- The integration test suite runs against a real Postgres (a throwaway
  `taidi_test` database, wiped between tests), including a genuine
  concurrency test using `asyncio.gather` against real HTTP requests — not a
  mock standing in for the database or the race condition.
- Switching to Supabase later (Phase 2's remaining step) touches
  `TAIDI_AUTH_MODE` / `TAIDI_SUPABASE_JWT_SECRET` / `TAIDI_DATABASE_URL` and
  nothing else in the API code.
