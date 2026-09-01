"use client";

import { getStoredAuth } from "./auth";
import type { GameRules, RoomState } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** A 409 carries {message, state} so the caller can resync without a refetch. */
export interface ConflictDetail {
  message: string;
  state: RoomState;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    const message =
      typeof detail === "string"
        ? detail
        : ((detail as { message?: string })?.message ?? `Request failed (${status})`);
    super(message);
    this.status = status;
    this.detail = detail;
  }

  get conflict(): ConflictDetail | null {
    return this.status === 409 ? (this.detail as ConflictDetail) : null;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const auth = getStoredAuth();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(auth ? { Authorization: `Bearer ${auth.token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      // no JSON body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  createRoom: () => post<RoomState>("/rooms"),
  byCode: (code: string) => request<{ room_id: string }>(`/rooms/by-code/${code}`),
  getState: (roomId: string) => request<RoomState>(`/rooms/${roomId}/state`),
  join: (roomId: string) => post<RoomState>(`/rooms/${roomId}/join`),
  start: (roomId: string, expectedSeq: number, rules?: Partial<GameRules>) =>
    post<RoomState>(`/rooms/${roomId}/start`, { expected_seq: expectedSeq, rules: rules ?? {} }),
  claimWin: (roomId: string, expectedSeq: number) =>
    post<RoomState>(`/rooms/${roomId}/win`, { expected_seq: expectedSeq }),
  submitCards: (roomId: string, expectedSeq: number, cards: number) =>
    post<RoomState>(`/rooms/${roomId}/cards`, { expected_seq: expectedSeq, cards }),
  submitFor: (roomId: string, expectedSeq: number, targetPlayer: string, cards: number) =>
    post<RoomState>(`/rooms/${roomId}/submit-for`, {
      expected_seq: expectedSeq,
      target_player: targetPlayer,
      cards,
    }),
  specialHand: (roomId: string, expectedSeq: number) =>
    post<RoomState>(`/rooms/${roomId}/special`, { expected_seq: expectedSeq }),
  voidLastRound: (roomId: string, expectedSeq: number) =>
    post<RoomState>(`/rooms/${roomId}/void`, { expected_seq: expectedSeq }),
  endGame: (roomId: string, expectedSeq: number) =>
    post<RoomState>(`/rooms/${roomId}/end`, { expected_seq: expectedSeq }),
};
