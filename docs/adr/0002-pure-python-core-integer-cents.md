# ADR-0002: `taidi_core` as a pure Python package; money in integer cents

- Status: accepted
- Date: 2026-09-01

## Context

ADR-0001 committed to event-sourced multiplayer rooms. Building that state
machine surfaced two implementation decisions worth recording on their own:
where the domain logic lives relative to any framework, and how money is
represented.

The existing scoring engine (`game.py`) is a `dataclass` + `pandas`-backed
`CardGameTracker`, with dollar amounts as `float` and players keyed by
display name. That's fine for a single Streamlit process, but the room state
machine needs to be replayed identically by an API server, tested with
property-based fuzzing, and eventually reused from a migration script —
none of which want a pandas dependency or float drift in a value that
represents real money owed between people.

## Decision

1. **`taidi_core` is a separate, installable package** (`core/`) with no
   dependency on Streamlit, pandas, or any I/O library — only `pydantic` for
   typed models. It has its own `pyproject.toml`, its own test suite, and is
   installed editable (`pip install -e ./core`) by anything that needs it.
   `taidi.py`/`ui.py`/`db.py` do **not** depend on it yet; the Streamlit app
   keeps using `game.py` until a later phase ports it over, so this phase
   carries zero risk to the deployed app.
2. **Every amount is an integer number of cents** (`card_value_cents`,
   `amount_cents`, `balances: dict[UUID, int]`, ...). Cents are always exact;
   there is no accumulated float error to reconcile, and the zero-sum
   invariant can be asserted with `==` instead of a tolerance. Display code
   converts to dollars only at the edge (`describe()`, and eventually the UI
   layer).
3. **Players are identified by `UUID`, never by display name.** Display
   names live only on `Member`/`PlayerStats`. This is what makes a player
   rename — already a first-class operation in the Streamlit app — a
   non-event in the new model instead of a data-rewrite.
4. **`ScoringRule` is a `Protocol` with one implementation** (`TaidiScoringRule`).
   A registry of pluggable game types was considered and cut: with a single
   real implementation, a protocol is enough to keep the seam, and a registry
   can be added when a second game actually needs one.

## Consequences

- The domain core can be property-tested (hypothesis) and type-checked
  (`mypy --strict`) in isolation, with a CI job that has nothing to do with
  Streamlit.
- Any future consumer — a FastAPI service, a CLI, another UI — imports the
  same package and gets the same validated behavior; there is exactly one
  place the scoring rules and the room state machine are implemented.
- The legacy engine (`game.py`) still exists and still uses dollars/names,
  because the deployed app depends on it. The migration script
  (`scripts/migrate_legacy_to_events.py`) is the bridge: it reconstructs raw
  inputs from legacy archives and replays them through `taidi_core`,
  asserting the resulting balances match the original totals to within a
  couple of cents (the only source of drift left, from the legacy code's
  float accumulation, not from the new engine).
