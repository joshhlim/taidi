"use client";

import { supabase } from "./auth";

/** All three trigger Supabase's USER_UPDATED auth event, which the existing
 * onAuthStateChange listeners in auth.ts already react to — so a change
 * here shows up immediately anywhere useStoredUser() is used, with no
 * extra wiring. Used by both the Settings page and, for password, the
 * password-recovery flow in /auth/callback. */

export async function updateDisplayName(name: string): Promise<void> {
  if (!supabase) throw new Error("Supabase auth is not configured.");
  const { error } = await supabase.auth.updateUser({ data: { display_name: name } });
  if (error) throw error;
}

/** Supabase emails a confirmation link to the new address before this
 * takes effect (and, if "Secure email change" is on, to the old one too). */
export async function updateEmail(newEmail: string): Promise<void> {
  if (!supabase) throw new Error("Supabase auth is not configured.");
  const { error } = await supabase.auth.updateUser({ email: newEmail });
  if (error) throw error;
}

export async function updatePassword(newPassword: string): Promise<void> {
  if (!supabase) throw new Error("Supabase auth is not configured.");
  const { error } = await supabase.auth.updateUser({ password: newPassword });
  if (error) throw error;
}
