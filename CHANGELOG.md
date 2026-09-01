# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

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
