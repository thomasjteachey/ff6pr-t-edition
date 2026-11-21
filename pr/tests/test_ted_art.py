"""T-Edition's art (tools/ted_art.py, tools/snes_sprites.py TEDITION): the decoder at moved tables, the monster recipe and
its rows, the looks table. Skips what needs the developer's ROMs."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ted_art as T  # noqa: E402

HAVE_TED = os.path.exists(T.TED_ROM)


class Recipe(unittest.TestCase):
    def test_monster_recipe(self):
        d = json.load(open(T.OUT, encoding="utf-8"))
        imgs = d["monster_images"]["images"]
        self.assertEqual(226, len(imgs))
        kinds = {}
        for a in d["assets"]:
            kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
            self.assertEqual(T.pr_id(a["monster"]), a["pr_id"])
            if a["kind"] != "swap":
                self.assertEqual(T.ASSET_BASE + a["monster"], a["asset_id"])
        self.assertEqual({"new": 174, "recolor": 52, "swap": 15}, kinds)
        keys = {i["key"] for i in imgs}
        for a in d["assets"]:
            if a["kind"] != "swap":
                self.assertIn(f"{a['group'].upper()}_B{a['monster']:03d}", keys)

    def test_looks_table(self):
        d = json.load(open(T.COSTUMES, encoding="utf-8"))["characters"]
        self.assertEqual(T.CAST, list(d))
        used = set()
        for c, name in enumerate(T.CAST):
            looks = d[name]
            self.assertEqual([0, 1, 2, 3, 4], [x["costume"] for x in looks])
            self.assertEqual(c, looks[0]["slot"])
            for k, rng in T.COSTUME_RANGES:
                self.assertIn(looks[k]["slot"], rng)
            used |= {x["slot"] for x in looks[1:]}
        self.assertEqual(56, len(used))


@unittest.skipUnless(HAVE_TED, "no T-Edition ROM")
class Rom(unittest.TestCase):
    rom = None

    @classmethod
    def setUpClass(cls):
        cls.rom = open(T.TED_ROM, "rb").read()

    def test_vanilla_layout_is_snes_sprites(self):
        import snes_sprites as SS
        a = SS.Sprites(type("R", (), {"data": self.rom, "b": lambda s, x, n: self.rom[x:x + n]})())
        b = SS.Sprites(self.rom, SS.VANILLA)            # raw bytes, the layout spelt out: the same reads
        for i in (0, 5, 200, 383):
            self.assertEqual(a.sprite(i).px, b.sprite(i).px)

    def test_tedition_layout(self):
        import snes_sprites as SS
        s = SS.Sprites(self.rom, SS.TEDITION)
        for i in (400, 420, 500):                        # one monster in each of T-Edition's tile banks
            sp = s.sprite(i)
            self.assertIsNotNone(SS.cropped(sp), i)

    def test_look_sizes(self):
        for s in (0, 27, 84):
            L = T.look(self.rom, s, 0)
            self.assertEqual(0x16A0, len(L["field"]))
            self.assertEqual(0x16A0, len(L["battle"]))
            self.assertEqual(0x320, len(L["portrait"]))
        self.assertNotEqual(T.look(self.rom, 0, 2)["battle"], T.look(self.rom, 0, 2)["field"])   # Terra: own battle sheet


if __name__ == "__main__":
    unittest.main()
