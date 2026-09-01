# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.3] - 2026-09-01

Discovered while actually creating the Supabase project: it uses a JWT
Signing Key (asymmetric), not the shared HS256 secret ADR-0005 assumed.
Supabase has moved newer projects to that model by default.

### Added
- JWKS-based JWT verification (`TAIDI_SUPABASE_URL`, via `PyJWKClient`),
  tried first when configured, falling back to the shared-secret path for
  older projects that still have one. `pyjwt[crypto]` added to `api/`'s
  dependencies — asymmetric algorithms silently don't work without
  `cryptography` installed; caught by the same clean-venv verification
  used for the Render build command, before it could fail in production.
- 5 new tests covering the JWKS path with a real generated EC keypair and
  a monkeypatched `PyJWKClient.fetch_data` (no live network call), plus a
  test proving JWKS wins when both a URL and a legacy secret are set.
- `render.yaml`, `api/.env.example`, and the README's deploy steps updated
  to ask which case a project is in and set the right variable.

## [0.3.2] - 2026-09-01

Groundwork for real accounts and a real deployment (ADR-0005) — Phase 3's
stats and rulesets need an identity that survives across sessions, which
`TAIDI_AUTH_MODE=dev`'s fresh-random-UUID-per-login can't provide.

### Added
- Supabase Auth support end to end: magic-link sign-in (`lib/auth.ts`'s
  `signInWithMagicLink`), an `/auth/callback` route that exchanges the
  emailed code for a session, and a `useStoredUser()`/`getStoredAuth()`
  surface that behaves identically to dev mode for every existing page —
  room/new pages needed zero changes. Display name rides in the JWT's
  `user_metadata`, exactly where the API's `_display_name_from_claims`
  already looked for it since ADR-0003.
- `TAIDI_AUTH_MODE=supabase` on the API: verifies real Supabase-issued
  tokens (checking `aud="authenticated"`, not just skipping audience
  verification as before) against the project's JWT secret. Verified with
  hand-crafted tokens matching Supabase's real claim shape — no project
  needed to prove the logic correct.
- `render.yaml`: a one-click Render Blueprint for the API, verified by
  installing into a genuinely clean virtualenv (not the developer's
  already-populated one) and confirming the server boots and serves.
- `statement_cache_size: 0` on the asyncpg engine — required once
  `TAIDI_DATABASE_URL` points at a pooled connection (e.g. Supabase's
  pgbouncer in transaction mode), harmless otherwise.
- Root README "Deploy the room app" section: the full Supabase → Render →
  Vercel sequence.

### Changed
- Local development is completely unaffected — `TAIDI_AUTH_MODE`/
  `NEXT_PUBLIC_AUTH_MODE` default to `dev` everywhere, and the full test
  and e2e suites were re-run against dev mode after every change in this
  release to confirm zero regression.

## [0.3.1] - 2026-09-01

App renamed to **GamBROle** (multi-game framing — Taidi is the first of
several games it'll host) and the "New Room" flow now matches that: pick a
game, then (for Taidi) configure every rule the old Streamlit app exposed
before the room is created.

### Added
- Rebrand: "GamBROle" across the manifest, page metadata, and home screen;
  new monogram icon (was Taidi's card-specific "2 of spades" mark).
- Home screen now has three post-login actions: New Room, Join Room, and
  My Stats (a real placeholder screen — "feature not available yet" —
  not a dead button).
- `/new`: pick a game (Taidi, Mahjong, Poker). Mahjong and Poker show the
  same not-available placeholder. Taidi shows the full rules editor —
  card value, base cards, double/triple multiplier toggle and thresholds,
  difference payouts, special hands toggle and value — matching every
  field the legacy Streamlit app exposed. The chosen rules travel with the
  room (held client-side until `start_game`, since the room can't apply
  rules until players have joined) and are what the game actually plays
  by, not just cosmetic.
- End-game screen now shows rounds played and a "so-and-so wins with
  $X" callout alongside the final standings, visible to every player's
  device the moment the game ends (already true structurally; this made
  it read as real final stats rather than just a balances list).
- e2e coverage for all of the above, including an exact-value assertion
  (a room created at $1.00/card resolves round 1 to precisely $29.00 for
  the winner) proving the configured rules reach the scoring engine, not
  just that *some* room got created.

### Fixed
- A real hydration bug, not just a test artifact: any returning user with
  a stored session hit `Hydration failed because the server rendered HTML
  didn't match the client` on every page load of `/`, `/new`, and
  `/room/{id}`. Cause: reading `localStorage` in a lazy `useState`
  initializer runs during SSR too (where there's no `window`, so it
  always resolves to "logged out"), while the client's first hydration
  pass resolves the real stored value — a guaranteed mismatch for anyone
  with an existing session. That lazy-init pattern was itself an earlier
  "fix" for an eslint `react-hooks/set-state-in-effect` warning; the
  correct fix was recognizing that a `localStorage` read is exactly the
  "subscribe to an external system" case that rule is meant to allow via
  an effect, not to avoid. Fixed with a shared `useStoredUser()` hook
  that defers the read to an effect and exposes a `checked` flag so
  auth-gated pages don't redirect a real user during the one-tick window
  before the check resolves. Verified via a targeted reload-with-existing-session
  repro (caught the bug, then confirmed clean) in addition to the full suite.

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
