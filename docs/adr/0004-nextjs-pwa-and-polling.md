# ADR-0004: Next.js PWA frontend; polling stands in for Realtime

- Status: accepted
- Date: 2026-09-01

## Context

ADR-0001 specified a PWA frontend reading room state via a managed realtime
layer (Supabase Realtime), writing only through the API (ADR-0003). Building
the first vertical slice — proving "a live room on two phones" end to end —
surfaced the last pieces of that design, and two real bugs worth recording
so they aren't reintroduced.

## Decision

1. **Next.js (App Router) + TypeScript + Tailwind**, all client components
   (`'use client'`) — the app is interactive throughout (live state,
   forms, `localStorage`), so there's little server-rendering advantage to
   chase here. Types for the API's JSON shape (`src/lib/types.ts`) are
   hand-kept against `taidi_core.models`, not generated, for now.
2. **Polling stands in for Supabase Realtime.** `usePolling` re-fetches
   `GET /rooms/{id}/state` every 1.5s. This is a deliberate, temporary
   substitute, not a corner cut on the read path's shape: the write path
   (every command, `expected_seq`, conflict handling) is exactly what
   Realtime will sit in front of later — swapping the polling hook for a
   Realtime subscription touches nothing else.
3. **A command's own conflict is not the same as failure.** The first
   version of the client's action handler treated any 409 as "show an
   error, drop what the player was doing." That's wrong for the common
   case: two players submit their card counts within the same poll
   window, one lands first, the second gets a 409 whose cause has nothing
   to do with whether *their* card count is valid. The fix — proven by the
   three-device Playwright test, which failed until this was in place — is
   that every command retries once against the fresh state returned in the
   409 body before surfacing anything to the player. This mirrors the
   API's own DB-level retry-once-on-race pattern (ADR-0003) one layer up.
4. **`data-testid` attributes on every interactive element and every piece
   of state the tests assert on** (`invite-code`, `win-btn`, `cards-input`,
   `standing-row`/`data-player`, `waiting-text`, `game-over`, ...), rather
   than matching on copy. UI text can change; the test contract shouldn't
   break when it does.
5. **Dev-mode auth end to end.** The e2e suite logs in three separate
   browser contexts as three separate dev-minted users — the same auth
   path a real device will use once `TAIDI_AUTH_MODE=supabase` is flipped,
   just without needing a Supabase project to exist yet.

## Consequences

- The three-device Playwright test (`e2e/full-game.spec.ts`) is the actual
  proof of this phase's "done when" bar: login → create/join by code →
  lobby converges to 3 members → start → win claim → simultaneous card
  submission from two independent browser contexts → round auto-resolves
  → special hand settles immediately and is visible to a third context →
  end game, all visible on every device without a shared page or manual
  refresh.
- Ports: the web dev server runs on `:3100`, not Next.js's default
  `:3000` — found the hard way, when Playwright's `reuseExistingServer`
  silently ran the suite against an unrelated project already listening on
  `:3000` on this machine. `reuseExistingServer` is off in this repo's
  config so a future port collision fails loudly instead of repeating that.
- `TAIDI_CORS_ORIGINS` must include whatever port the browser actually runs
  on; it defaults to both `:3000` and `:3100`.
- Migrating to Realtime later replaces `usePolling`'s effect body with a
  subscription callback; `setData` is already the seam that decision
  will plug into.
