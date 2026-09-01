"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import {
  devLogin,
  getStoredAuth,
  signInWithMagicLink,
  signOut,
  supabase,
  type CurrentUser,
} from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();
  // See useStoredUser's doc comment in lib/auth.ts — a lazy initializer
  // here would mismatch server vs. first-client-hydration render for any
  // returning user. This needs its own setter (handleLogin updates it
  // immediately) so it can't just use that shared hook.
  const [user, setUser] = useState<CurrentUser | null>(null);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUser(getStoredAuth()?.user ?? null);
  }, []);
  const [nameInput, setNameInput] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [codeInput, setCodeInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkSent, setLinkSent] = useState(false);

  async function handleDevLogin(e: React.FormEvent) {
    e.preventDefault();
    const name = nameInput.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      const auth = await devLogin(name);
      setUser(auth.user);
    } catch {
      setError("Couldn't sign in. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    const email = emailInput.trim();
    const name = nameInput.trim();
    if (!email || !name) return;
    setBusy(true);
    setError(null);
    try {
      await signInWithMagicLink(email, name);
      setLinkSent(true);
    } catch {
      setError("Couldn't send the sign-in link. Try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    setUser(null);
  }

  async function handleJoinRoom(e: React.FormEvent) {
    e.preventDefault();
    const code = codeInput.trim().toUpperCase();
    if (!code) return;
    setBusy(true);
    setError(null);
    try {
      const { room_id } = await api.byCode(code);
      router.push(`/room/${room_id}`); // the room page itself handles joining
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't find that room.");
      setBusy(false);
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <div className="mx-auto mb-4 h-14 w-14 rounded-2xl bg-brand flex items-center justify-center">
            <span className="text-gold font-serif text-2xl font-bold">G</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-brand">
            Gam<span className="text-gold">BRO</span>le
          </h1>
        </div>

        {!user ? (
          supabase ? (
            linkSent ? (
              <p data-testid="link-sent" className="text-center text-sm text-muted">
                Check your email for a sign-in link.
              </p>
            ) : (
              <form onSubmit={handleMagicLink} className="space-y-3">
                <input
                  className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-brand-strong"
                  data-testid="display-name-input"
                  placeholder="Your name"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  autoFocus
                />
                <input
                  type="email"
                  className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-brand-strong"
                  data-testid="email-input"
                  placeholder="you@example.com"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={busy || !nameInput.trim() || !emailInput.trim()}
                  data-testid="continue-btn"
                  className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
                >
                  Send sign-in link
                </button>
              </form>
            )
          ) : (
            <form onSubmit={handleDevLogin} className="space-y-3">
              <input
                className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-brand-strong"
                data-testid="display-name-input"
                placeholder="Your name"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                autoFocus
              />
              <button
                type="submit"
                disabled={busy || !nameInput.trim()}
                data-testid="continue-btn"
                className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                Continue
              </button>
            </form>
          )
        ) : (
          <div className="space-y-6">
            <p className="text-center text-sm text-muted">
              Signed in as <span className="font-semibold text-foreground">{user.display_name}</span>
            </p>

            <button
              onClick={() => router.push("/new")}
              disabled={busy}
              data-testid="new-room-btn"
              className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              New Room
            </button>

            <form onSubmit={handleJoinRoom} className="space-y-3">
              <input
                className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-center tracking-widest uppercase outline-none focus:border-brand-strong"
                data-testid="room-code-input"
                placeholder="Room code"
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                maxLength={6}
              />
              <button
                type="submit"
                disabled={busy || !codeInput.trim()}
                data-testid="join-room-btn"
                className="w-full rounded-xl border border-border py-3 text-sm font-semibold text-brand disabled:opacity-50"
              >
                Join Room
              </button>
            </form>

            <button
              onClick={() => router.push("/stats")}
              data-testid="my-stats-btn"
              className="w-full rounded-xl border border-border py-3 text-sm font-semibold text-muted"
            >
              My Stats
            </button>

            <button
              onClick={handleSignOut}
              data-testid="sign-out-btn"
              className="w-full text-center text-xs text-muted"
            >
              Sign out
            </button>
          </div>
        )}

        {error && <p className="mt-4 text-center text-sm text-danger">{error}</p>}
      </div>
    </main>
  );
}
