"""T-Edition EX's boss room (tools/ted_ex*.py): the fights, the AI export, the scenes, the Magicite folder.

    .venv/Scripts/python -m unittest tests.test_ted_ex      (~25 s; needs the two Mato ROMs in build/t-edition)
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import ted_ex as X  # noqa: E402

HAVE_ROMS = os.path.exists(X.EX_ROM) and os.path.exists(X.TED_ROM)


@unittest.skipUnless(HAVE_ROMS, "T-Edition's ROMs aren't built")
class Fights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = X.Roms()
        cls.fights = X.fights(cls.R)
        cls.rec = X.ex_records(cls.R)

    def test_thirteen_fights(self):
        self.assertEqual(len(self.fights), 13)
        self.assertEqual(sorted(f["formation"] for f in self.fights),
                         [768, 769, 771, 773, 775, 776, 777, 778, 780, 785, 788, 789, 792])
        bits = [f["bit"] for f in self.fights if f["bit"] is not None]
        self.assertEqual(sorted(bits), sorted((0x267, 0x268, 0x269, 0x26A, 0x26C, 0x26D, 0x275, 0x2A1, 0x2C1, 0x2C2, 0, 2)))

    def test_ids(self):
        self.assertEqual(X.EX_IDS[256], 512)
        self.assertEqual(X.EX_IDS[282], 538)
        self.assertEqual(X.EX_IDS[X.OMEGA_WEAPON], 539)
        self.assertEqual(self.rec["monster_names"][539], "Omega Weapon")
        self.assertEqual(self.rec["monster_items"][539], X.OMEGA_REWARD)

    def test_merged_phases(self):
        golbez = self.rec["formation_monsters"][769]
        self.assertEqual([(m[0], m[3]) for m in golbez], [(513, True), (514, False)])
        ark = self.rec["formation_monsters"][785]
        self.assertEqual(sum(1 for m in ark if m[3]), 1)
        self.assertEqual(len(ark), 5)


@unittest.skipUnless(HAVE_ROMS, "T-Edition's ROMs aren't built")
class Ai(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ted_ex_ai as AI
        cls.AI = AI
        cls.sai, cls.texts = AI.export(log=lambda *a: None)

    def ops(self, i):
        import snes_ai as A
        raw = bytes.fromhex(self.sai["scripts"][i])
        m, c = A.parse(raw, 0)
        return m + c

    def test_no_formation_change_left(self):
        for i in self.sai["scripts"]:
            self.assertNotIn("formation", [n for n, _ in self.ops(i)], i)

    def test_golbez_second_form(self):
        # F2 to formation 2 -> show slot 1 refilled, hide slot 0; his "unhide monster 0" after it -> slot 1
        en = [a for n, a in self.ops(513) if n == "enemies"]
        self.assertIn((0x0B, 0, 2), en)
        self.assertIn((0x0B, 4, 1), en)
        self.assertIn((8, 0, 2), en)

    def test_lines_on_free_numbers(self):
        used = set()
        R = X.Roms()
        for e in range(512):
            m, c = X.ai(R.ted, e, data=X.TED_AI_DATA)
            used |= {a[0] for n, a in m + c if n == "message"}
        self.assertFalse(set(map(int, self.sai["message_keys"])) & used)
        self.assertEqual(len(self.sai["message_keys"]), 28)
        self.assertTrue(self.texts["TEDX_BTL_01_0"].startswith("We are the Cloud of Darkness"))

    def test_party_cells(self):
        import ted_ex_ai as AI
        rows, specials = AI.port_data()
        if not rows:
            self.skipTest("no port with EX's parties yet")
        sai, _ = AI.export(party_rows=rows, specials=specials, log=lambda *a: None)
        for p, mem in sai["party_members"].items():
            cells = [m[1] for m in mem if m]
            self.assertEqual(len(cells), len(set(cells)), p)            # one member per cell
            self.assertTrue(all(m[0] >= 512 for m in mem if m), p)
        golbez = sai["party_members"][30769]
        self.assertEqual([m[2:] for m in golbez if m], [[1, 1], [0, 0]])  # second form: hidden, brought in by F5

    def test_attacks(self):
        self.assertEqual(len(self.sai["attack_overrides"]), 31)
        self.assertEqual(self.sai["attack_overrides"][184], 7184)
        self.assertEqual(len(self.sai["attacks"]), 256)
        self.assertEqual(self.sai["copies"][1539], 539)


@unittest.skipUnless(HAVE_ROMS, "T-Edition's ROMs aren't built")
class Scenes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ted_ex_events as XE
        cls.res, cls.texts, cls.alloc = XE.translate(log=lambda *a: None)

    def test_moogle(self):
        name, sc, after, t = self.res[0]
        self.assertEqual(sum(t.stubs.values()), 0)
        enc = [m for m in sc["Mnemonics"] if m["mnemonic"] == "Encount"]
        self.assertEqual(sorted(m["operands"]["iValues"][0] for m in enc),
                         sorted(30000 + f for f in (768, 769, 771, 773, 775, 776, 777, 778, 780, 785, 788, 789, 792)))
        sel = [m for m in sc["Mnemonics"] if m["mnemonic"] == "Select"]
        self.assertEqual(len(sel), 5)                    # four menu pages and Omega's
        self.assertEqual(self.texts["story_mes_en"]["TEDX_E1263_c_01"], "Omega Weapon")

    def test_win_flags(self):
        name, sc, after, t = self.res[0]
        flags = sorted(m["operands"]["iValues"][0] for _, a, _ in after for m in a["Mnemonics"]
                       if m["mnemonic"] == "SetFlag" and m["operands"]["sValues"][0] == "ScenarioFlag4")
        self.assertEqual(flags, list(range(5, 18)))
        for _, a, _ in after:                            # no game-over scene after a win
            self.assertFalse([m for m in a["Mnemonics"] if m["mnemonic"] == "SysCall"])

    def test_shops(self):
        for name, sc, after, t in self.res[1:3]:
            calls = [m["operands"]["sValues"][0] for m in sc["Mnemonics"] if m["mnemonic"] == "SysCall"]
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0].startswith("TED:shop 922"))


@unittest.skipUnless(HAVE_ROMS, "T-Edition's ROMs aren't built")
class Folder(unittest.TestCase):
    def test_builds_and_merges(self):
        import ted_ex_build as B
        import magicite_merge as MM
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "TEditionEX")
            changed = B.build(out=out, log=lambda *a: None, with_room=False)   # the room takes ~90 s: see Room
            self.assertEqual(len(changed["ability"]), 31)
            self.assertEqual(sorted(changed["product_group"]), [9228, 9229])
            self.assertEqual(len(changed["script"]), 16)
            self.assertTrue(all(9700 <= i < 9800 for i in changed["script"]))
            dest = os.path.join(tmp, "merged")
            os.makedirs(dest)
            rep = MM.merge(dest, [out], log=lambda *a: None)
            self.assertEqual(rep.conflicts, [])

    def test_door_file(self):
        import ted_ex_build as B
        door = B.mog_house_door()["467"]
        self.assertEqual(door["exits"][0]["to"], [780, 1])
        self.assertEqual(door["points"][0]["point_id"], 90)
        self.assertFalse([t for t in door["tiles"] if (t[0], t[1] & 0x3F) in B.OLD_DOOR])
        self.assertEqual(len(door["tiles"]), 4)


class Room(unittest.TestCase):
    """The room as the last `tools/ted_ex_build.py` wrote it (mods/TEditionEX)."""

    def test_room_objects(self):
        import glob
        import json
        hits = glob.glob(os.path.join(HERE, "..", "mods", "TEditionEX", "map_*", "**", "Map_*_90", "entity_default.json"),
                         recursive=True)
        if not hits:
            self.skipTest("mods/TEditionEX has no room yet (run tools/ted_ex_build.py)")
        objs = {}
        for lay in json.load(open(hits[0], encoding="utf-8"))["layers"]:
            for o in lay.get("objects") or []:
                objs[o["name"]] = {q["name"]: q["value"] for q in o["properties"]}
        self.assertEqual((objs["GotoMap"]["map_id"], objs["GotoMap"]["point_id"]), (700, 90))
        self.assertEqual(objs["PointIn"]["object_id"], 1)
        self.assertEqual(objs["EX Moogle"]["script_id"], 9700)


if __name__ == "__main__":
    unittest.main()
