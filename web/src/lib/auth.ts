"use client";

import { useEffect, useState } from "react";

const TOKEN_KEY = "taidi_token";
const USER_KEY = "taidi_user";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CurrentUser {
  user_id: string;
  display_name: string;
}

export interface StoredAuth {
  token: string;
  user: CurrentUser;
}

export function getStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  const rawUser = window.localStorage.getItem(USER_KEY);
  if (!token || !rawUser) return null;
  try {
    return { token, user: JSON.parse(rawUser) as CurrentUser };
  } catch {
    return null;
  }
}

export function storeAuth(auth: StoredAuth): void {
  window.localStorage.setItem(TOKEN_KEY, auth.token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
}

export function clearAuth(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export interface AuthCheck {
  user: CurrentUser | null;
  /** False until the client-only localStorage read has actually run.
   * Consumers that redirect on `!user` MUST wait for this — otherwise
   * a genuinely signed-in user gets bounced during the one-tick window
   * before the read resolves. */
  checked: boolean;
}

/**
 * Read-only access to the signed-in user, safe for SSR.
 *
 * A lazy `useState(() => getStoredAuth()?.user)` initializer looks
 * tempting but is wrong here: it runs during the server render too, where
 * there's no `window` and it always resolves to null, while the client's
 * *first hydration render* would resolve to the real stored user whenever
 * one already exists — a mismatch React has to discard and re-render for.
 * Deferring the read to an effect keeps server and first-client-render
 * identical (both null), then updates once mounted. This is exactly the
 * "subscribe to an external system" case react-hooks/set-state-in-effect
 * is meant to allow, not the derived-state case it warns about.
 */
export function useStoredUser(): AuthCheck {
  const [state, setState] = useState<AuthCheck>({ user: null, checked: false });
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ user: getStoredAuth()?.user ?? null, checked: true });
  }, []);
  return state;
}

/**
 * Dev-mode login only (TAIDI_AUTH_MODE=dev on the API) — mints a token for
 * any display name, no external identity provider. Swap for Supabase Auth
 * once a project exists; nothing downstream of storeAuth() needs to change.
 */
export async function devLogin(displayName: string): Promise<StoredAuth> {
  const res = await fetch(`${API_URL}/auth/dev-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!res.ok) {
    throw new Error(`Login failed: ${res.status}`);
  }
  const data = await res.json();
  const auth: StoredAuth = {
    token: data.access_token,
    user: { user_id: data.user_id, display_name: data.display_name },
  };
  storeAuth(auth);
  return auth;
}
