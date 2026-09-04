"""Golden fixtures for MahjongRules' default tai_table — the "3/6 半"
preset. Hand-copied from the stakes table the product owner gave, so this
test would catch an accidental edit to the defaults, not just a broken
lookup mechanism (that's what test_mahjong_engine_properties.py covers)."""

from __future__ import annotations

from mahjong_core.models import MahjongRules

EXPECTED = {
    1: (4, 4),
    2: (7, 5),
    3: (11, 7),
    4: (20, 12),
    5: (40, 22),
}


def test_default_rules_are_the_3_6_ban_preset():
    rules = MahjongRules()
    assert rules.base_chips == 300
    assert rules.yao_chips == 2
    assert rules.gang_chips == 2
    assert rules.max_tai == 5
    for tai, (hu, zimo) in EXPECTED.items():
        assert rules.tai_table[tai].hu == hu
        assert rules.tai_table[tai].zimo == zimo
