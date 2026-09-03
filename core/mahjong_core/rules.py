"""Pure money-math for YAO, GANG, and HU declarations.

No state, no player resolution — machine.py owns "who pays whom" (it needs
RoomState to resolve seats to players anyway); this module only answers
"how much", so it's trivial to golden-fixture test in isolation. See
ADR-0006 and the plan's settlement table for the source of these formulas.
"""

from __future__ import annotations

from .models import MahjongRules

ENGINE_VERSION = "mahjong-1"


def yao_amount(rules: MahjongRules, an: bool) -> int:
    return rules.yao_unit_cents * (2 if an else 1)


def gang_amount_self(rules: MahjongRules) -> int:
    return rules.gang_unit_cents


def gang_amount_other(rules: MahjongRules) -> int:
    return rules.gang_unit_cents * 3


def gang_amount_angang(rules: MahjongRules) -> int:
    return rules.gang_unit_cents * 2


def hu_amount_direct(rules: MahjongRules, tai: int) -> int:
    return rules.tai_unit_cents * tai


def hu_amount_zimo_each(rules: MahjongRules, tai: int) -> int:
    return rules.zimo_unit_cents * tai


def hu_amount_bao(rules: MahjongRules, tai: int) -> int:
    return rules.zimo_unit_cents * tai * 3
