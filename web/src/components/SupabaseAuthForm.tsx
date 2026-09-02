"use client";

import { useState } from "react";
import { requestPasswordReset, signInWithPassword, signUpWithPassword, type CurrentUser } from "@/lib/auth";

type View = "login" | "signup" | "forgot";

const inputCls =
  "w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-brand-strong";

export default function SupabaseAuthForm({ onSignedIn }: { onSignedIn: (user: CurrentUser) => void }) {
  const [view, setView] = useState<View>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function switchView(v: View) {
    setError(null);
    setNotice(null);
    setPassword("");
    setConfirmPassword("");
    setView(v);
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const auth = await signInWithPassword(email.trim(), password);
      onSignedIn(auth.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't sign in.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    try {
      const auth = await signUpWithPassword(email.trim(), password, name.trim());
      if (auth) {
        onSignedIn(auth.user);
      } else {
        // "Confirm email" is enabled on the project — account exists but
        // needs the confirmation link clicked before it can sign in.
        // switchView clears `notice`, so it must run first or this message
        // never shows (both setNotice calls land in the same React batch,
        // and the later one wins).
        switchView("login");
        setNotice("Account created — check your email to confirm it, then log in.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't create an account.");
    } finally {
      setBusy(false);
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestPasswordReset(email.trim());
      setNotice("Check your email for a password reset link.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't send the reset link.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {view === "login" && (
        <form onSubmit={handleLogin} className="space-y-3">
          <input
            type="email"
            data-testid="email-input"
            placeholder="you@example.com"
            className={inputCls}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
          <input
            type="password"
            data-testid="password-input"
            placeholder="Password"
            className={inputCls}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="submit"
            disabled={busy || !email.trim() || !password}
            data-testid="continue-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Log In
          </button>
          <div className="flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => switchView("forgot")}
              data-testid="forgot-password-link"
              className="text-muted"
            >
              Forgot password?
            </button>
            <button
              type="button"
              onClick={() => switchView("signup")}
              data-testid="show-signup-link"
              className="font-semibold text-brand"
            >
              Create an account
            </button>
          </div>
        </form>
      )}

      {view === "signup" && (
        <form onSubmit={handleSignup} className="space-y-3">
          <input
            data-testid="display-name-input"
            placeholder="Your name"
            className={inputCls}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <input
            type="email"
            data-testid="email-input"
            placeholder="you@example.com"
            className={inputCls}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            data-testid="password-input"
            placeholder="Password"
            className={inputCls}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <input
            type="password"
            data-testid="confirm-password-input"
            placeholder="Confirm password"
            className={inputCls}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          <button
            type="submit"
            disabled={busy || !name.trim() || !email.trim() || !password}
            data-testid="signup-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Create Account
          </button>
          <button
            type="button"
            onClick={() => switchView("login")}
            data-testid="show-login-link"
            className="w-full text-center text-xs text-muted"
          >
            Already have an account? Log in
          </button>
        </form>
      )}

      {view === "forgot" && (
        <form onSubmit={handleForgot} className="space-y-3">
          <p className="text-center text-xs text-muted">
            Enter your email and we&apos;ll send a link to reset your password.
          </p>
          <input
            type="email"
            data-testid="email-input"
            placeholder="you@example.com"
            className={inputCls}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            disabled={busy || !email.trim()}
            data-testid="send-reset-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Send Reset Link
          </button>
          <button
            type="button"
            onClick={() => switchView("login")}
            data-testid="show-login-link"
            className="w-full text-center text-xs text-muted"
          >
            Back to log in
          </button>
        </form>
      )}

      {notice && (
        <p data-testid="auth-notice" className="text-center text-sm text-muted">
          {notice}
        </p>
      )}
      {error && (
        <p data-testid="auth-error" className="text-center text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
