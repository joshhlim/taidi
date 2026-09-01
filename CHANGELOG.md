# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-09-01

Phase 2: the first live-room vertical slice, end to end — a room where
every player acts from their own device, proven by a Playwright test that
drives three separate browser contexts through a full game with no shared
page and no manual refresh.

### Added
- `api/`: a FastAPI backend wrapping `taidi_core` as the sole write path to
  a room's event log (ADR-0003). Endpoints for create/join-by-code/state and
  every room command (start, win, cards, submit-for, special, void, end),
  each mapping `taidi_core.machine`'s `SeqConflict`/`NotAuthorized`/
  `IllegalTransition` to 409/403/400.
- Pluggable auth: `TAIDI_AUTH_MODE=dev` (default) mints local tokens via
  `POST /auth/dev-login` with no external identity provider; `supabase`
  mode verifies against a real Supabase project's JWT secret instead — same
  code path either way.
- Postgres schema (`rooms`, `events`) with `UNIQUE(room_id, seq)` as a
  second concurrency guard beneath the state machine's own check; Alembic
  migrations targeting `TAIDI_DATABASE_URL` directly.
- `docker-compose.yml`: an isolated local Postgres (project `taidi`, port
  5433) — no cloud account needed for local development.
- `web/`: a Next.js PWA — dev sign-in, new room / join by code, a lobby
  that converges as players join, and a live table (Win, per-player card
  entry, special hands settling immediately, end game), all driven by
  polling `GET /rooms/{id}/state` as a deliberate, swappable stand-in for
  Supabase Realtime (ADR-0004).
- `e2e/full-game.spec.ts`: three independent browser contexts play a full
  game through the real UI against the real API and a real database —
  the actual proof of this phase's "two phones" bar.
- 10 API integration tests (real Postgres, incl. a concurrency test with
  `asyncio.gather` against real HTTP requests) + the e2e suite. `mypy
  --strict` clean on both Python packages; CI runs a Postgres service, an
  Alembic upgrade/downgrade/upgrade round-trip, and the full Playwright
  suite on every push.
- `core/taidi_core` is now PEP 561 typed (`py.typed`) so consuming packages'
  `mypy --strict` runs pick up its inline types automatically.

### Fixed
- A command's own 409 conflict was being treated as failure, discarding
  the player's in-flight action (e.g. their card count) even when it had
  nothing to do with the conflict. Every command now retries once against
  the fresh state before surfacing an error — caught by the three-device
  Playwright test, which failed until this was in place.
- (backend, before release) `_as_json`'s own body was accidentally
  overwritten into a call to itself during a find-and-replace, causing
  infinite recursion on every response; caught immediately by the existing
  test suite.

## [0.2.0] - 2026-09-01

Phase 1 of the roadmap: `taidi_core`, a standalone, pure-Python domain
package implementing the multiplayer room design from ADR-0001. Not yet
wired into the deployed Streamlit app — this release proves the design in
isolation, with its own test suite and CI job.

### Added
- `core/taidi_core`: typed models (`GameRules`, `Transfer`, `RoundState`,
  `RoomState`, `Event`, `PlayerStats`, `Settlement`), the scoring engine
  (`rules.py`, integer cents), the room/round state machine (`machine.py`:
  `join_player`, `start_game`, `claim_win`, `submit_cards`, `submit_for`,
  `add_special_hand`, `void_last_round`, `end_game`, `apply`, `fold`),
  lifetime stats (`stats.py`), and settlement (`settlement.py`: pairwise
  netting and greedy debt minimization).
- 45 tests for the core package: golden fixtures per rule toggle, hypothesis
  property tests (zero-sum, winner-never-pays, determinism), and full state
  machine coverage including a flagship full-simulated-game test and a
  replay-from-scratch determinism test. `mypy --strict` passes.
- `scripts/migrate_legacy_to_events.py`: reconstructs raw round inputs from
  legacy archived-game transfers and replays them through `taidi_core`,
  verifying the resulting balances match the original totals to within a
  couple of cents (float-accumulation tolerance).
- ADR-0002: pure Python core package, integer cents, UUID player identity.
- CI now also runs the core package's tests and `mypy --strict` on every push.

### Fixed
- (in `taidi_core`, not the legacy engine) voiding a round no longer
  reverses special-hand transfers claimed during it — special hands settle
  independently of round resolution and must survive an undo.

## [0.1.0] - 2026-09-01

First versioned release of the Streamlit scorekeeper app.

### Added
- Home-screen navigation: New Game, Continue Game, Analytics, Settings.
- Fully configurable rules (card value, base payout, double/triple thresholds,
  difference payouts, special hands) and saved rulesets.
- Autosaving games with undo, continue-later, and explicit finish.
- Lifetime analytics: leaderboard, per-player profit/loss trend, per-game history.
- Player management: add, rename (propagates through all games), remove.
- Game management: edit balances/rules of ongoing games, edit totals of
  finished games, delete either.
- Persistence in SQLite locally or Turso in the cloud.
- Optional shared passcode gate (`APP_PASSCODE`).
- JSON backup export and restore.
- Test suite and GitHub Actions CI (ruff + pytest).
