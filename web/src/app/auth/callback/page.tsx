"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/auth";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const [exchangeError, setExchangeError] = useState<string | null>(null);

  useEffect(() => {
    // Missing code / unconfigured supabase are derived from render-time
    // data (searchParams), not an external system — nothing to do here
    // for those; only the actual token exchange belongs in an effect.
    if (!supabase || !code) return;
    supabase.auth.exchangeCodeForSession(code).then(({ error }) => {
      if (error) {
        setExchangeError(error.message);
      } else {
        router.replace("/");
      }
    });
  }, [code, router]);

  const staticError = !supabase
    ? "Sign-in isn't configured in this environment."
    : !code
      ? "This sign-in link is missing or already used."
      : null;
  const error = staticError ?? exchangeError;

  return (
    <main className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm text-center space-y-3">
        {error ? (
          <>
            <p className="text-sm text-danger">{error}</p>
            <Link href="/" className="text-sm font-semibold text-brand">
              Back to sign in
            </Link>
          </>
        ) : (
          <p className="text-sm text-muted">Signing you in…</p>
        )}
      </div>
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
