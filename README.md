# Taidi Tracker

Score keeping & settlements for Big Two (Taidi) nights. Configurable house
rules, autosaving games, lifetime analytics.

## Run locally

```bash
pip install -r requirements.txt
streamlit run taidi.py
```

Data is stored in a local `taidi.db` SQLite file.

### Develop

```bash
pip install -r requirements-dev.txt
pytest -q            # engine, persistence, and end-to-end AppTest suites
ruff check . && ruff format --check .
```

CI runs the same checks on every push and pull request.

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
for the design and `CHANGELOG.md` for progress.

## Structure

| File      | Purpose                                              |
| --------- | ---------------------------------------------------- |
| `taidi.py`| Entry point and page routing                         |
| `game.py` | Game rules, scoring engine, lifetime stats           |
| `db.py`   | Persistence (local SQLite or Turso)                  |
| `ui.py`   | All rendering: CSS, home screen, pages               |
