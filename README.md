# Taidi Tracker

Score keeping & settlements for Big Two (Taidi) nights. Configurable house
rules, autosaving games, lifetime analytics.

## Run locally

All Python packages in this repo (the Streamlit app, `taidi_core`, and the
FastAPI backend) share one virtualenv at the repo root — create it once:

```bash
python3 -m venv .venv
source .venv/bin/activate   # every session, before running anything Python
pip install -r requirements.txt
streamlit run taidi.py
```

Data is stored in a local `taidi.db` SQLite file.

### Develop

```bash
source .venv/bin/activate   # if not already active
pip install -r requirements-dev.txt   # installs taidi_core and taidi_api editable too
pytest tests -q       # legacy app: engine, persistence, end-to-end AppTest suites
pytest core/tests -q  # taidi_core: scoring engine + room state machine
ruff check . && ruff format --check .
mypy --config-file core/pyproject.toml core/taidi_core
```

CI runs the same checks on every push and pull request (in a fresh runner,
which is its own isolation — no venv needed there).

### Optional passcode

Set `APP_PASSCODE = "..."` in secrets to require a shared passcode before the
app opens. Leave it unset for no gate.

### Backups

Settings → Games → Backup downloads a JSON export of everything; the same
panel restores one (replacing all current data).

## Deploy (Streamlit Community Cloud + Turso)

1. Push this repo to GitHub.
2. Create a free database at [turso.tech](https://turso.tech); copy its URL and
   an auth token.
3. Create the app at [share.streamlit.io](https://share.streamlit.io) pointing
   at `taidi.py`, and add to the app secrets:

   ```toml
   TURSO_DATABASE_URL = "libsql://<db>-<org>.turso.io"
   TURSO_AUTH_TOKEN = "<token>"
   ```

When those secrets are present the app stores everything in Turso (survives
redeploys and restarts); without them it falls back to the local file.

## Roadmap

The app is evolving from a single-scorekeeper tool into a multiplayer room
where every player acts from their own phone. See
[docs/adr/0001-event-sourced-multiplayer-rooms.md](docs/adr/0001-event-sourced-multiplayer-rooms.md)
and [docs/adr/0002-pure-python-core-integer-cents.md](docs/adr/0002-pure-python-core-integer-cents.md)
for the design, and `CHANGELOG.md` for progress.

`core/taidi_core` is the new domain package implementing that design,
`api/` is a FastAPI backend built on it, and `web/` is the Next.js PWA
frontend — none of it is wired into the deployed app yet (see `db.py`/
`ui.py` below for what actually runs in production today). The full slice
runs locally: `docker compose up -d postgres`, then see
[api/README.md](api/README.md) and [web/README.md](web/README.md).
`web/e2e/full-game.spec.ts` drives three browser contexts through a full
game as the end-to-end proof.

## Structure

### Deployed app (Streamlit)

| File      | Purpose                                              |
| --------- | ---------------------------------------------------- |
| `taidi.py`| Entry point and page routing                         |
| `game.py` | Game rules, scoring engine, lifetime stats           |
| `db.py`   | Persistence (local SQLite or Turso)                  |
| `ui.py`   | All rendering: CSS, home screen, pages               |

### `core/` — `taidi_core`, the multiplayer domain package

A separate, installable package (own `pyproject.toml`, own tests) with no
Streamlit/pandas dependency — see ADR-0002.

| Module                     | Purpose                                                    |
| --------------------------- | ----------------------------------------------------------- |
| `taidi_core/models.py`      | Typed vocabulary: `GameRules`, `Transfer`, `RoundState`, `RoomState`, `Event`, `PlayerStats`, `Settlement` |
| `taidi_core/rules.py`       | The scoring engine (card transfers, special-hand transfers) |
| `taidi_core/machine.py`     | The room/round event-sourced state machine                  |
| `taidi_core/stats.py`       | Lifetime stats derived from ended rooms                     |
| `taidi_core/settlement.py`  | Pairwise netting and greedy debt minimization                |
| `scripts/migrate_legacy_to_events.py` | Migrates legacy Streamlit archives into `taidi_core` rooms, verifying balances match |

### `api/` — FastAPI backend

The only write path to a room — see [api/README.md](api/README.md) and
ADR-0003. `docker-compose.yml` at the repo root runs a local Postgres for it.

| Module | Purpose |
| --- | --- |
| `app/db.py` | Schema (`rooms`, `events`) and session management |
| `app/auth.py` | Pluggable JWT auth: dev-mode token minting or Supabase verification |
| `app/events_store.py` | Persistence + folding the event log back into a `RoomState` |
| `app/routers/rooms.py` | The room command endpoints |
| `alembic/` | Migrations |

### `web/` — Next.js PWA frontend

See [web/README.md](web/README.md) and ADR-0004.

| Path | Purpose |
| --- | --- |
| `src/app/page.tsx` | Home: sign-in, new room, join by code |
| `src/app/room/[roomId]/page.tsx` | Lobby, live table, ended-game views |
| `src/lib/api.ts` | Typed fetch client; auto-retries a command once on 409 |
| `src/lib/usePolling.ts` | Stands in for Supabase Realtime for now |
| `e2e/full-game.spec.ts` | Three-device end-to-end proof |
