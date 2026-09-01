"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/auth";
import { updatePassword } from "@/lib/account";

const inputCls =
  "w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-brand-strong";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const [exchangeError, setExchangeError] = useState<string | null>(null);
  const [isRecovery, setIsRecovery] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    if (!supabase || !code || ran.current) return;
    ran.current = true;

    // Supabase fires PASSWORD_RECOVERY as part of processing the exchange
    // below when this link came from a password-reset email — captured via
    // a plain closure variable (not state) so it's readable synchronously
    // once the exchange's promise resolves, no extra render needed.
    let recovery = false;
    const { data: sub } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") recovery = true;
    });

    supabase.auth.exchangeCodeForSession(code).then(({ error }) => {
      sub.subscription.unsubscribe();
      if (error) {
        setExchangeError(error.message);
      } else if (recovery) {
        setIsRecovery(true);
      } else {
        router.replace("/");
      }
    });

    return () => sub.subscription.unsubscribe();
  }, [code, router]);

  async function handleSetPassword(e: React.FormEvent) {
    e.preventDefault();
    setSaveError(null);
    if (password.length < 6) {
      setSaveError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setSaveError("Passwords don't match.");
      return;
    }
    setBusy(true);
    try {
      await updatePassword(password);
      setSaved(true);
      setTimeout(() => router.replace("/"), 1200);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Couldn't update the password.");
    } finally {
      setBusy(false);
    }
  }

  const staticError = !supabase
    ? "Sign-in isn't configured in this environment."
    : !code
      ? "This link is missing or already used."
      : null;
  const error = staticError ?? exchangeError;

  if (error) {
    return (
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm text-center space-y-3">
          <p className="text-sm text-danger">{error}</p>
          <Link href="/" className="text-sm font-semibold text-brand">
            Back to sign in
          </Link>
        </div>
      </main>
    );
  }

  if (isRecovery) {
    return (
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm space-y-4">
          <h1 className="text-center text-lg font-extrabold text-brand">Set a new password</h1>
          {saved ? (
            <p data-testid="password-reset-saved" className="text-center text-sm text-muted">
              Password updated — signing you in…
            </p>
          ) : (
            <form onSubmit={handleSetPassword} className="space-y-3">
              <input
                type="password"
                data-testid="new-password-input"
                placeholder="New password"
                className={inputCls}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
              <input
                type="password"
                data-testid="confirm-new-password-input"
                placeholder="Confirm new password"
                className={inputCls}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
              <button
                type="submit"
                disabled={busy || !password}
                data-testid="save-new-password-btn"
                className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                Save Password
              </button>
              {saveError && <p className="text-center text-sm text-danger">{saveError}</p>}
            </form>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 flex items-center justify-center px-6 py-12">
      <p className="text-sm text-muted">Signing you in…</p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <CallbackInner />
    </Suspense>
  );
}
