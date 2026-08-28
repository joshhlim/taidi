# Taidi Tracker

Score keeping & settlements for Big Two (Taidi) nights. Configurable house
rules, autosaving games, lifetime analytics.

## Run locally

```bash
pip install -r requirements.txt
streamlit run taidi.py
```

Data is stored in a local `taidi.db` SQLite file.

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

## Structure

| File      | Purpose                                              |
| --------- | ---------------------------------------------------- |
| `taidi.py`| Entry point and page routing                         |
| `game.py` | Game rules, scoring engine, lifetime stats           |
| `db.py`   | Persistence (local SQLite or Turso)                  |
| `ui.py`   | All rendering: CSS, home screen, pages               |
