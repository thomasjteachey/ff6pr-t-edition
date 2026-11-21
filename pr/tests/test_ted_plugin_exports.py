"""TedPlugin's data from T-Edition's ROM (TedPlugin session, 2026-11-21): the exports its new features read.

    .venv/Scripts/python -m unittest tests/test_ted_plugin_exports.py

Skipped without Mato's ROM (build/t-edition). Checks:
  * chest lines (audit U9, ted_plugin_data.chest_lines / chest_rule): 14, one per character, each with (ITEM_N), <CT> on
    every line of the key's text;
  * weapon details (audit U5, weapon_details): the weapons T-Edition's weapon guide names (Rune Blade MP Critical, Blood
    Sword HP Absorb, Soul Eater MP Absorb, Dragon Spear dragons, Shuriken humans, Cards flying);
  * Near Fatal immunity (audit M17): 229 of 512 monsters (spec 48);
  * battle lines (audit T8, ted_dialog.BattleMessages): Mato's moved table decodes (Ultros's message 4), TED_BTL_ keys.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PR, "tools"))
MATO = os.path.join(os.path.dirname(PR), "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
ITEMS = os.path.join(PR, "mods", "TEditionPort", "ted_items.json")


@unittest.skipUnless(os.path.exists(MATO), "no Mato ROM")
class Exports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import profile_tedition as T
        import ff6snes as S
        import ted_plugin_data as X
        T.build()
        cls.X, cls.rom, cls.raw = X, S.Rom(T.MATO), open(T.MATO, "rb").read()
        cls.T = T

    def test_chest_lines(self):
        lines = self.X.chest_lines()
        self.assertEqual(len(lines), 14)
        for t in lines:
            self.assertIn("(ITEM_N)", t)
            self.assertTrue(t.startswith("<CT>"))
        self.assertTrue(lines[1].startswith("<CT>(ROCK):"), lines[1])   # Locke's, his name as the PR's tag
        with tempfile.TemporaryDirectory() as d:
            self.X.chest_rule(d, log=lambda *_: None)
            path = os.path.join(d, "message", "Assets", "GameAssets", "Serial", "Data", "Message", "system_en.txt")
            keys = dict(line.rstrip("\r\n").split("\t", 1) for line in open(path, encoding="utf-8"))
            self.assertEqual(sorted(keys), [f"TED_CHEST_{c:02d}" for c in range(14)])
            for v in keys.values():
                self.assertEqual(v.count("\\n"), v.count("\\n<CT>"), v)   # every line centred

    @unittest.skipUnless(os.path.exists(ITEMS), "no port (ted_items.json)")
    def test_weapon_details(self):
        w = self.X.weapon_details(self.rom)
        names = {r["name"].strip(): int(s) for s, r in json.load(open(ITEMS, encoding="utf-8"))["items"].items()}
        want = {"Rune Blade": "MP Critical", "Blood Sword": "HP Absorb", "Soul Eater": "MP Absorb",
                "Dragon Spear": "Bonus vs dragons", "Shuriken": "Bonus vs humans", "Cards": "Bonus vs flying"}
        for name, label in want.items():
            with self.subTest(name=name):
                self.assertIn(label, w.get(names[name], []))

    def test_near_fatal_immune(self):
        n = sum(1 for e in range(512) if self.raw[self.T.MONSTERS + 32 * e + 0x15] & 0x02)
        self.assertEqual(n, 229)

    def test_monster_kinds(self):
        # audit I3: T-Edition's pre-damage table (C2/3DB5) checks $3C95 = monster byte $12: E -> bit 0, F -> bit 5
        rom = self.raw
        for bit, n in ((0x01, 111), (0x20, 51)):
            self.assertEqual(sum(1 for e in range(512) if rom[self.T.MONSTERS + 32 * e + 0x12] & bit), n)
        self.assertEqual([rom[0x023DB5 + 2 * k] | rom[0x023DB6 + 2 * k] << 8 for k in (8, 14, 15)], [0x38EE, 0x3EB2, 0x3EBE])

    def test_battle_lines(self):
        import ted_dialog as D
        b = D.BattleMessages()
        keys = b(4)
        self.assertEqual(keys[0], "TED_BTL_004_01")
        self.assertEqual(b.texts[keys[0]], "Ultros: Thwarted again!")
        self.assertEqual(b(9) and b.texts[b(9)[0]], "*sploosh*! *blub blub*...")


if __name__ == "__main__":
    unittest.main()
