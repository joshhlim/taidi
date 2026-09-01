"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useStoredUser } from "@/lib/auth";
import { usePolling } from "@/lib/usePolling";
import type { GameRules, RoomState } from "@/lib/types";

/** Rules chosen on /new before the room existed — see that page for why
 * this can't just be sent at room-creation time. */
function readStoredRules(roomId: string): Partial<GameRules> | undefined {
  try {
    const raw = sessionStorage.getItem(`gambrole_rules_${roomId}`);
    return raw ? (JSON.parse(raw) as GameRules) : undefined;
  } catch {
    return undefined;
  }
}

function money(cents: number): string {
  const dollars = Math.abs(cents) / 100;
  return `${cents < 0 ? "-" : ""}$${dollars.toFixed(2)}`;
}

export default function RoomPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const router = useRouter();
  const { user, checked } = useStoredUser();
  const [banner, setBanner] = useState<string | null>(null);
  const [cardsInput, setCardsInput] = useState("");
  const [busy, setBusy] = useState(false);
  const joinedRef = useRef(false);

  useEffect(() => {
    // Wait for the client-only auth check to actually complete — redirecting
    // on the pre-check `user === null` would bounce a genuinely signed-in
    // user before useStoredUser's own effect has resolved.
    if (checked && !user) router.replace("/");
  }, [checked, user, router]);

  const { data: state, setData } = usePolling<RoomState>(
    () => api.getState(roomId),
    1500,
    [roomId, user?.user_id],
  );

  const me = user?.user_id;
  const isMember = !!(state && me && me in state.members);

  // Auto-join once: if we landed here via a shared link/code without having
  // joined yet, and the room is still in its lobby, join automatically.
  useEffect(() => {
    if (!state || !me || joinedRef.current) return;
    if (!isMember && state.status === "lobby") {
      joinedRef.current = true;
      api
        .join(roomId)
        .then(setData)
        .catch((e) => setBanner(e instanceof ApiError ? e.message : "Couldn't join this room."));
    }
  }, [state, me, isMember, roomId, setData]);

  /**
   * Runs a command against the room's current seq. A 409 means someone
   * else's event landed first — that doesn't invalidate what THIS player
   * is trying to do (their own card count, a special-hand claim, ...), so
   * we resync to the fresh state and retry once against the new seq before
   * giving up. Only a second failure (or a non-seq error) surfaces to the
   * player.
   */
  async function run<T>(action: (seq: number) => Promise<T>) {
    setBusy(true);
    setBanner(null);
    let seq = state?.seq;
    for (let attempt = 0; attempt < 2; attempt++) {
      if (seq === undefined) break;
      try {
        const result = await action(seq);
        setBusy(false);
        return result;
      } catch (e) {
        if (e instanceof ApiError && e.conflict) {
          setData(e.conflict.state);
          seq = e.conflict.state.seq;
          continue; // retry once against the fresh seq
        }
        setBanner(e instanceof ApiError ? e.message : "Something went wrong.");
        setBusy(false);
        return null;
      }
    }
    setBanner("Someone else keeps acting first — try again.");
    setBusy(false);
    return null;
  }

  const membersBySeat = useMemo(
    () => (state ? Object.values(state.members).sort((a, b) => a.seat - b.seat) : []),
    [state],
  );
  const standings = useMemo(
    () =>
      state
        ? Object.entries(state.balances).sort(([, a], [, b]) => b - a)
        : [],
    [state],
  );
  const currentRound = state && state.rounds.length > 0 ? state.rounds[state.rounds.length - 1] : null;

  if (!user || !state) {
    return <main className="flex-1 flex items-center justify-center text-muted text-sm">Loading…</main>;
  }

  const isHost = state.host_id === me;
  const nameOf = (id: string) => state.members[id]?.display_name ?? "?";

  return (
    <main className="flex-1 px-5 py-8 max-w-md mx-auto w-full">
      {banner && (
        <div className="mb-4 rounded-lg border border-border bg-surface px-4 py-2 text-sm text-muted">
          {banner}
        </div>
      )}

      {state.status === "lobby" && (
        <Lobby
          state={state}
          isHost={isHost}
          isMember={isMember}
          membersBySeat={membersBySeat}
          busy={busy}
          onJoin={() => run((_seq) => api.join(roomId)).then((r) => r && setData(r))}
          onStart={() =>
            run((seq) => api.start(roomId, seq, readStoredRules(roomId))).then((r) => r && setData(r))
          }
        />
      )}

      {state.status === "in_progress" && currentRound && me && (
        <TableView
          state={state}
          me={me}
          currentRound={currentRound}
          standings={standings}
          nameOf={nameOf}
          busy={busy}
          cardsInput={cardsInput}
          setCardsInput={setCardsInput}
          onClaimWin={() => run((seq) => api.claimWin(roomId, seq)).then((r) => r && setData(r))}
          onSubmitCards={(cards) =>
            run((seq) => api.submitCards(roomId, seq, cards)).then((r) => {
              if (r) {
                setData(r);
                setCardsInput("");
              }
            })
          }
          onSpecialHand={() =>
            run((seq) => api.specialHand(roomId, seq)).then((r) => r && setData(r))
          }
          onEndGame={() => run((seq) => api.endGame(roomId, seq)).then((r) => r && setData(r))}
        />
      )}

      {state.status === "ended" && (
        <EndedView
          standings={standings}
          nameOf={nameOf}
          roundsPlayed={state.rounds.length}
          onHome={() => router.push("/")}
        />
      )}
    </main>
  );
}

function Lobby({
  state,
  isHost,
  isMember,
  membersBySeat,
  busy,
  onJoin,
  onStart,
}: {
  state: RoomState;
  isHost: boolean;
  isMember: boolean;
  membersBySeat: RoomState["members"][string][];
  busy: boolean;
  onJoin: () => void;
  onStart: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <p className="text-xs uppercase tracking-widest text-muted mb-1">Room code</p>
        <p data-testid="invite-code" className="text-3xl font-extrabold tracking-[0.3em] text-brand">{state.invite_code}</p>
      </div>

      <div>
        <p className="text-xs uppercase tracking-widest text-muted mb-2">Players</p>
        <div className="space-y-2">
          {membersBySeat.map((m) => (
            <div
              key={m.player_id}
              data-testid="lobby-member"
              className="rounded-xl border border-border bg-surface px-4 py-3 text-sm font-medium"
            >
              {m.display_name}
              {m.player_id === state.host_id && <span className="ml-2 text-xs text-gold">HOST</span>}
            </div>
          ))}
        </div>
      </div>

      {!isMember ? (
        <button
          onClick={onJoin}
          disabled={busy}
          data-testid="lobby-join-btn"
          className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          Join Room
        </button>
      ) : isHost ? (
        <button
          onClick={onStart}
          disabled={busy || membersBySeat.length < 2}
          data-testid="start-game-btn"
          className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          {membersBySeat.length < 2 ? "Waiting for more players…" : "Start Game"}
        </button>
      ) : (
        <p className="text-center text-sm text-muted">Waiting for the host to start…</p>
      )}
    </div>
  );
}

function TableView({
  state,
  me,
  currentRound,
  standings,
  nameOf,
  busy,
  cardsInput,
  setCardsInput,
  onClaimWin,
  onSubmitCards,
  onSpecialHand,
  onEndGame,
}: {
  state: RoomState;
  me: string;
  currentRound: NonNullable<RoomState["rounds"][number]>;
  standings: [string, number][];
  nameOf: (id: string) => string;
  busy: boolean;
  cardsInput: string;
  setCardsInput: (v: string) => void;
  onClaimWin: () => void;
  onSubmitCards: (cards: number) => void;
  onSpecialHand: () => void;
  onEndGame: () => void;
}) {
  const isPlaying = currentRound.phase === "playing";
  const isCollecting = currentRound.phase === "collecting";
  const iAmWinner = currentRound.winner === me;
  const haveSubmitted = me in currentRound.cards_submitted;
  const pending = Object.keys(state.members).filter(
    (id) => id !== currentRound.winner && !(id in currentRound.cards_submitted),
  );

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted mb-2">
          Round {currentRound.round_no}
        </p>
        <div className="space-y-2">
          {standings.map(([playerId, cents], idx) => (
            <div
              key={playerId}
              data-testid="standing-row"
              data-player={nameOf(playerId)}
              className={`flex items-center justify-between rounded-xl border px-4 py-3 text-sm ${
                idx === 0 ? "border-gold bg-[#FFF8E1]" : "border-border bg-surface"
              }`}
            >
              <span className="font-medium">{nameOf(playerId)}</span>
              <span data-testid="standing-amount" className={`font-bold ${cents < 0 ? "text-danger" : "text-brand-strong"}`}>
                {money(cents)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {isPlaying && (
        <div className="space-y-3">
          <button
            onClick={onClaimWin}
            disabled={busy}
            data-testid="win-btn"
            className="w-full rounded-xl bg-brand py-4 text-base font-bold text-white disabled:opacity-50"
          >
            Win
          </button>
          {state.rules?.special_hands_enabled && (
            <button
              onClick={onSpecialHand}
              disabled={busy}
              data-testid="special-hand-btn"
              className="w-full rounded-xl border border-border py-3 text-sm font-semibold text-brand disabled:opacity-50"
            >
              Special Hand
            </button>
          )}
        </div>
      )}

      {isCollecting && iAmWinner && (
        <p data-testid="waiting-text" className="text-center text-sm text-muted">
          Waiting for {pending.map(nameOf).join(", ")}…
        </p>
      )}

      {isCollecting && !iAmWinner && !haveSubmitted && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const n = Number(cardsInput);
            if (Number.isInteger(n) && n >= 0) onSubmitCards(n);
          }}
          className="space-y-3"
        >
          <p className="text-sm text-center text-muted">
            {nameOf(currentRound.winner ?? "")} won — how many cards were you left with?
          </p>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            data-testid="cards-input"
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-center text-lg outline-none focus:border-brand-strong"
            value={cardsInput}
            onChange={(e) => setCardsInput(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            disabled={busy || cardsInput.trim() === ""}
            data-testid="submit-cards-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Submit
          </button>
        </form>
      )}

      {isCollecting && !iAmWinner && haveSubmitted && (
        <p data-testid="waiting-text" className="text-center text-sm text-muted">
          Waiting for {pending.map(nameOf).join(", ")}…
        </p>
      )}

      <button
        onClick={onEndGame}
        disabled={busy}
        data-testid="end-game-btn"
        className="w-full rounded-xl border border-border py-2.5 text-xs font-semibold text-muted disabled:opacity-50"
      >
        End Game
      </button>
    </div>
  );
}

function EndedView({
  standings,
  nameOf,
  roundsPlayed,
  onHome,
}: {
  standings: [string, number][];
  nameOf: (id: string) => string;
  roundsPlayed: number;
  onHome: () => void;
}) {
  const [topId, topCents] = standings[0] ?? [null, 0];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <p data-testid="game-over" className="text-lg font-extrabold text-brand">
          Game Over
        </p>
        <p className="text-xs uppercase tracking-widest text-muted">
          {roundsPlayed} round{roundsPlayed === 1 ? "" : "s"} played
        </p>
      </div>

      {topId && (
        <p className="text-center text-sm text-muted">
          <span className="font-semibold text-foreground">{nameOf(topId)}</span> wins with{" "}
          <span className="font-bold text-brand-strong">{money(topCents)}</span>
        </p>
      )}

      <div className="space-y-2">
        {standings.map(([playerId, cents], idx) => (
          <div
            key={playerId}
            data-testid="standing-row"
            data-player={nameOf(playerId)}
            className={`flex items-center justify-between rounded-xl border px-4 py-3 text-sm ${
              idx === 0 ? "border-gold bg-[#FFF8E1]" : "border-border bg-surface"
            }`}
          >
            <span className="font-medium">{nameOf(playerId)}</span>
            <span
              data-testid="standing-amount"
              className={`font-bold ${cents < 0 ? "text-danger" : "text-brand-strong"}`}
            >
              {money(cents)}
            </span>
          </div>
        ))}
      </div>
      <button
        onClick={onHome}
        data-testid="back-to-home-btn"
        className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white"
      >
        Back to Home
      </button>
    </div>
  );
}
