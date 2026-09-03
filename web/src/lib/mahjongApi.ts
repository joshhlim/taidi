"use client";

import { post, request } from "./api";
import type { MahjongRoomState, MahjongRules } from "./mahjongTypes";

export const mahjongApi = {
  getState: (roomId: string) => request<MahjongRoomState>(`/rooms/${roomId}/state`),
  join: (roomId: string) => post<MahjongRoomState>(`/rooms/${roomId}/mahjong/join`),
  leave: (roomId: string, expectedSeq: number) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/leave`, { expected_seq: expectedSeq }),
  disband: (roomId: string, expectedSeq: number) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/disband`, { expected_seq: expectedSeq }),
  assignSeats: (roomId: string, expectedSeq: number, seatMap: Record<string, number>) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/assign-seats`, {
      expected_seq: expectedSeq,
      seat_map: seatMap,
    }),
  start: (roomId: string, expectedSeq: number, rules?: Partial<MahjongRules>) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/start`, {
      expected_seq: expectedSeq,
      rules: rules ?? {},
    }),
  declareYao: (roomId: string, expectedSeq: number, targetSeat: number, an: boolean) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/yao`, {
      expected_seq: expectedSeq,
      target_seat: targetSeat,
      an,
    }),
  declareGang: (roomId: string, expectedSeq: number, target: number | "angang") =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/gang`, {
      expected_seq: expectedSeq,
      target,
    }),
  declareHu: (
    roomId: string,
    expectedSeq: number,
    mode: "direct" | "zimo" | "bao",
    targetSeat: number | null,
    tai: number,
  ) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/hu`, {
      expected_seq: expectedSeq,
      mode,
      target_seat: targetSeat,
      tai,
    }),
  declareNoWin: (roomId: string, expectedSeq: number) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/no-win`, { expected_seq: expectedSeq }),
  continueWind: (roomId: string, expectedSeq: number) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/continue-wind`, {
      expected_seq: expectedSeq,
    }),
  endGame: (roomId: string, expectedSeq: number) =>
    post<MahjongRoomState>(`/rooms/${roomId}/mahjong/end`, { expected_seq: expectedSeq }),
};
