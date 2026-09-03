"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useStoredUser } from "@/lib/auth";
import type { GameRules, GameType } from "@/lib/types";
import type { MahjongRules } from "@/lib/mahjongTypes";

const DEFAULT_RULES: GameRules = {
  card_value_cents: 20,
  base_cards: 2,
  multipliers_enabled: true,
  double_threshold: 10,
  triple_threshold: 13,
  difference_payouts: true,
  special_hands_enabled: true,
  special_hand_cards: 5,
};

const DEFAULT_MAHJONG_RULES: MahjongRules = {
  yao_unit_cents: 100,
  gang_unit_cents: 100,
  tai_unit_cents: 100,
  zimo_unit_cents: 100,
  max_tai: 10,
};

const MAHJONG_PRESETS: { label: string; rules: MahjongRules }[] = [
  {
    label: "Casual",
    rules: { yao_unit_cents: 50, gang_unit_cents: 50, tai_unit_cents: 50, zimo_unit_cents: 50, max_tai: 10 },
  },
  {
    label: "Standard",
    rules: { yao_unit_cents: 100, gang_unit_cents: 100, tai_unit_cents: 100, zimo_unit_cents: 100, max_tai: 10 },
  },
  {
    label: "High Stakes",
    rules: { yao_unit_cents: 200, gang_unit_cents: 200, tai_unit_cents: 200, zimo_unit_cents: 200, max_tai: 13 },
  },
];

const GAMES = [
  { id: "taidi", label: "Taidi", available: true },
  { id: "mahjong", label: "Mahjong", available: true },
  { id: "poker", label: "Poker", available: false },
] as const;

type GameId = (typeof GAMES)[number]["id"];

const inputCls =
  "w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand-strong";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-muted mb-1">{label}</span>
      {children}
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 text-sm cursor-pointer">
      <span className="font-medium">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 accent-brand-strong"
      />
    </label>
  );
}

export default function NewRoomPage() {
  const router = useRouter();
  const { user, checked } = useStoredUser();
  const [selected, setSelected] = useState<GameId | null>(null);
  const [rules, setRules] = useState<GameRules>(DEFAULT_RULES);
  const [mahjongRules, setMahjongRules] = useState<MahjongRules>(DEFAULT_MAHJONG_RULES);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // See the matching comment in room/[roomId]/page.tsx — must wait for
    // checked, or a genuinely signed-in user gets bounced before the
    // client-only auth read resolves.
    if (checked && !user) router.replace("/");
  }, [checked, user, router]);

  function set<K extends keyof GameRules>(key: K, value: GameRules[K]) {
    setRules((r) => ({ ...r, [key]: value }));
  }

  function setMahjong<K extends keyof MahjongRules>(key: K, value: MahjongRules[K]) {
    setMahjongRules((r) => ({ ...r, [key]: value }));
  }

  async function handleCreate(gameType: GameType) {
    setBusy(true);
    setError(null);
    try {
      // The room only takes rules at start_game time (once the lobby is
      // full), so we hold onto what was configured here until then.
      const created = await api.createRoom(gameType);
      const chosenRules = gameType === "mahjong" ? mahjongRules : rules;
      sessionStorage.setItem(`gambrole_rules_${created.room_id}`, JSON.stringify(chosenRules));
      router.push(`/room/${created.room_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't create a room.");
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <main className="flex-1 px-5 py-8 max-w-md mx-auto w-full">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => (selected ? setSelected(null) : router.push("/"))}
          data-testid="back-btn"
          className="h-11 w-11 rounded-full border border-border flex items-center justify-center text-lg font-bold text-brand"
        >
          ←
        </button>
        <h1 className="text-lg font-extrabold text-brand">New Room</h1>
      </div>

      {!selected ? (
        <div className="space-y-3">
          {GAMES.map((g) => (
            <button
              key={g.id}
              onClick={() => setSelected(g.id)}
              data-testid={`game-tile-${g.id}`}
              className="w-full rounded-xl border border-border bg-surface px-4 py-4 text-left"
            >
              <p className="font-semibold">{g.label}</p>
              {!g.available && <p className="text-xs text-muted mt-0.5">Coming soon</p>}
            </button>
          ))}
        </div>
      ) : selected === "poker" ? (
        <div className="space-y-4 text-center py-8">
          <p data-testid="not-available" className="text-sm text-muted">
            Feature not available yet.
          </p>
          <button onClick={() => setSelected(null)} className="text-sm font-semibold text-brand">
            Choose another game
          </button>
        </div>
      ) : selected === "mahjong" ? (
        <div className="space-y-5">
          <div>
            <p className="text-xs text-muted mb-2">Presets</p>
            <div className="grid grid-cols-3 gap-2">
              {MAHJONG_PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setMahjongRules(p.rules)}
                  data-testid={`mahjong-preset-${p.label.toLowerCase().replace(" ", "-")}`}
                  className="rounded-xl border border-border bg-surface px-2 py-2 text-xs font-semibold"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="咬 YAO ($)">
              <input
                type="number"
                step={0.05}
                min={0}
                data-testid="rule-yao"
                value={mahjongRules.yao_unit_cents / 100}
                onChange={(e) => setMahjong("yao_unit_cents", Math.round((Number(e.target.value) || 0) * 100))}
                className={inputCls}
              />
            </Field>
            <Field label="槓 GANG ($)">
              <input
                type="number"
                step={0.05}
                min={0}
                data-testid="rule-gang"
                value={mahjongRules.gang_unit_cents / 100}
                onChange={(e) => setMahjong("gang_unit_cents", Math.round((Number(e.target.value) || 0) * 100))}
                className={inputCls}
              />
            </Field>
            <Field label="Per 台 TAI ($)">
              <input
                type="number"
                step={0.05}
                min={0}
                data-testid="rule-tai"
                value={mahjongRules.tai_unit_cents / 100}
                onChange={(e) => setMahjong("tai_unit_cents", Math.round((Number(e.target.value) || 0) * 100))}
                className={inputCls}
              />
            </Field>
            <Field label="自摸 Zimo per 台 ($)">
              <input
                type="number"
                step={0.05}
                min={0}
                data-testid="rule-zimo"
                value={mahjongRules.zimo_unit_cents / 100}
                onChange={(e) => setMahjong("zimo_unit_cents", Math.round((Number(e.target.value) || 0) * 100))}
                className={inputCls}
              />
            </Field>
          </div>

          <Field label="Max 台 TAI">
            <input
              type="number"
              min={1}
              data-testid="rule-max-tai"
              value={mahjongRules.max_tai}
              onChange={(e) => setMahjong("max_tai", Math.max(1, Number(e.target.value) || 1))}
              className={inputCls}
            />
          </Field>

          {error && <p className="text-sm text-center text-danger">{error}</p>}

          <button
            onClick={() => handleCreate("mahjong")}
            disabled={busy}
            data-testid="create-room-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Create Room
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Value per card ($)">
              <input
                type="number"
                step={0.05}
                min={0}
                data-testid="rule-card-value"
                value={rules.card_value_cents / 100}
                onChange={(e) => set("card_value_cents", Math.round((Number(e.target.value) || 0) * 100))}
                className={inputCls}
              />
            </Field>
            <Field label="Base cards to winner">
              <input
                type="number"
                min={0}
                value={rules.base_cards}
                onChange={(e) => set("base_cards", Number(e.target.value) || 0)}
                className={inputCls}
              />
            </Field>
          </div>

          <Toggle
            label="Double / triple penalties"
            checked={rules.multipliers_enabled}
            onChange={(v) => set("multipliers_enabled", v)}
          />
          {rules.multipliers_enabled && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="×2 at ≥">
                <input
                  type="number"
                  min={1}
                  value={rules.double_threshold}
                  onChange={(e) => set("double_threshold", Number(e.target.value) || 1)}
                  className={inputCls}
                />
              </Field>
              <Field label="×3 at ≥">
                <input
                  type="number"
                  min={1}
                  value={rules.triple_threshold}
                  onChange={(e) => set("triple_threshold", Number(e.target.value) || 1)}
                  className={inputCls}
                />
              </Field>
            </div>
          )}

          <Toggle
            label="Difference payouts between losers"
            checked={rules.difference_payouts}
            onChange={(v) => set("difference_payouts", v)}
          />

          <Toggle
            label="Special hands"
            checked={rules.special_hands_enabled}
            onChange={(v) => set("special_hands_enabled", v)}
          />
          {rules.special_hands_enabled && (
            <Field label="Cards per special hand">
              <input
                type="number"
                min={1}
                value={rules.special_hand_cards}
                onChange={(e) => set("special_hand_cards", Number(e.target.value) || 1)}
                className={inputCls}
              />
            </Field>
          )}

          {error && <p className="text-sm text-center text-danger">{error}</p>}

          <button
            onClick={() => handleCreate("taidi")}
            disabled={busy}
            data-testid="create-room-btn"
            className="w-full rounded-xl bg-brand py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Create Room
          </button>
        </div>
      )}
    </main>
  );
}
