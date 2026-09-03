// Mirrors mahjong_core's RoomState.model_dump(mode="json") exactly — see
// core/mahjong_core/models.py. Keep in sync by hand for now, same as
// types.ts does for Taidi.

import type { Member, RoomStatus } from "./types";

export type TransferKind = "yao" | "gang" | "hu" | "bao";

export interface MahjongRules {
  yao_unit_cents: number;
  gang_unit_cents: number;
  tai_unit_cents: number;
  zimo_unit_cents: number;
  max_tai: number;
}

export interface MahjongTransfer {
  from_player: string;
  to_player: string;
  amount_cents: number;
  kind: TransferKind;
  hand_no: number;
}

export interface HandState {
  hand_no: number;
  wind: number;
  dealer_seat: number;
  had_gang: boolean;
  closed: boolean;
  winner: string | null;
  transfers: MahjongTransfer[];
}

export interface MahjongRoomState {
  room_id: string;
  game_type: "mahjong";
  status: RoomStatus;
  seq: number;
  host_id: string;
  members: Record<string, Member>;
  rules: MahjongRules | null;
  hands: HandState[];
  balances: Record<string, number>;
  created_at: string;
  ended_at: string | null;
  pending_wind_decision: boolean;
  invite_code: string;
}

// Fixed seat nicknames — seats are plain 0-3 ints on the wire; these labels
// are purely a frontend display concern (the backend never sees them).
export const SEAT_LABELS = [
  { han: "東", pinyin: "DONG" },
  { han: "南", pinyin: "NAN" },
  { han: "西", pinyin: "XI" },
  { han: "北", pinyin: "BEI" },
] as const;
