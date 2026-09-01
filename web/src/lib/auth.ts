"use client";

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
